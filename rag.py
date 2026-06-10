"""Embedding, vector store, retrieval, and grounded generation for The Unofficial Guide.

Spec (planning.md, by Jaed Pizarro): all-MiniLM-L6-v2 embeddings via sentence-transformers,
ChromaDB persistent store, top-k=4 retrieval, grounded generation via Groq
llama-3.3-70b-versatile with programmatic source attribution.

AI-assisted implementation; reviewed by Jaed.
"""
import json
import os
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE = Path(__file__).parent
CHUNKS_PATH = BASE / "chunks.json"
DB_PATH = os.environ.get("CHROMA_DB_PATH", str(BASE / "chroma_db"))
COLLECTION = "fiu_dining"
EMBED_MODEL = "all-MiniLM-L6-v2"
TOP_K = 4

_model = None
_collection = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)  # downloads once, then cached locally
    return _model


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=DB_PATH)
        _collection = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    return _collection


def build_index():
    """Embed all chunks and load them into ChromaDB with source metadata."""
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    col = get_collection()
    model = get_model()
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False).tolist()
    col.upsert(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[c["metadata"] for c in chunks],
    )
    print(f"Indexed {col.count()} chunks into '{COLLECTION}' at {DB_PATH}")


def retrieve(query: str, k: int = TOP_K):
    """Return top-k chunks: list of dicts with text, metadata, distance."""
    emb = get_model().encode([query]).tolist()
    res = get_collection().query(query_embeddings=emb, n_results=k)
    out = []
    for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        out.append({"text": text, "metadata": meta, "distance": round(dist, 3)})
    return out


SYSTEM_PROMPT = """You are The Unofficial Guide, answering FIU students' questions about campus dining.
Answer the question using ONLY the information in the provided documents.
If the documents don't contain enough information to answer, say exactly: "I don't have enough information on that in my documents."
Do not use general knowledge about FIU or college dining. Keep answers concise (2-4 sentences)."""


def generate(query: str, k: int = TOP_K):
    """Grounded answer + programmatic source attribution. Returns dict with answer, sources, chunks."""
    from groq import Groq  # imported here so retrieval works without an API key

    chunks = retrieve(query, k=k)
    context = "\n\n".join(
        f"[Document: {c['metadata']['title']} ({c['metadata']['source_file']})]\n{c['text']}"
        for c in chunks
    )
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Documents:\n{context}\n\nQuestion: {query}"},
        ],
        temperature=0.2,
    )
    answer = resp.choices[0].message.content
    # Source attribution is appended programmatically -- guaranteed, not left to the LLM.
    sources = sorted({f"{c['metadata']['title']} -- {c['metadata']['source_file']}" for c in chunks})
    return {"answer": answer, "sources": sources, "chunks": chunks}


def ask(question: str):
    """End-to-end helper used by the Gradio app."""
    result = generate(question)
    return {"answer": result["answer"], "sources": result["sources"]}


if __name__ == "__main__":
    build_index()
