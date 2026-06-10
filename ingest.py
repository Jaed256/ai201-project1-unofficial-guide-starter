"""Document ingestion + chunking pipeline for The Unofficial Guide (FIU campus dining).

Implements the spec in planning.md:
- Load raw .txt documents from data/raw/ (each has a metadata header: SOURCE/URL/TITLE/AUTHOR/DATE)
- Clean: strip metadata header into structured metadata, normalize whitespace
- Chunk: paragraph-based, merging small paragraphs up to a target size of 500-800 chars
- Output: chunks.json with text + metadata (source file, title, URL, chunk index)

AI-assisted implementation (documented in README AI usage section); spec decisions by Jaed Pizarro.
"""
import json
import re
from pathlib import Path

RAW_DIR = Path(__file__).parent / "data" / "raw"
OUT_PATH = Path(__file__).parent / "data" / "chunks.json"

MIN_CHUNK = 200   # merge paragraphs until at least this size
MAX_CHUNK = 800   # split/flush before exceeding this

HEADER_KEYS = ("SOURCE:", "URL:", "TITLE:", "AUTHOR:", "AUTHORS:", "DATE:")


def parse_document(path: Path):
    """Split a raw file into (metadata dict, body text)."""
    text = path.read_text(encoding="utf-8")
    meta = {"source_file": path.name}
    body_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        matched = False
        for key in HEADER_KEYS:
            if stripped.startswith(key):
                meta[key.rstrip(":").lower()] = stripped[len(key):].strip()
                matched = True
                break
        if not matched:
            body_lines.append(line)
    body = "\n".join(body_lines)
    # normalize: collapse 3+ newlines, strip trailing spaces
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return meta, body


def chunk_paragraphs(body: str):
    """Paragraph-based chunking: merge small paragraphs, flush before MAX_CHUNK."""
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        candidate = (current + "\n\n" + para).strip() if current else para
        if len(candidate) <= MAX_CHUNK:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # paragraph itself longer than MAX_CHUNK: split on sentences
            if len(para) > MAX_CHUNK:
                current = ""
                for sent in re.split(r"(?<=[.!?])\s+", para):
                    cand = (current + " " + sent).strip() if current else sent
                    if len(cand) <= MAX_CHUNK:
                        current = cand
                    else:
                        if current:
                            chunks.append(current)
                        current = sent
            else:
                current = para
    if current:
        chunks.append(current)
    # merge any trailing tiny chunk into its predecessor
    merged = []
    for c in chunks:
        if merged and len(c) < MIN_CHUNK and len(merged[-1]) + len(c) <= MAX_CHUNK + 200:
            merged[-1] = merged[-1] + "\n\n" + c
        else:
            merged.append(c)
    return merged


def main():
    all_chunks = []
    files = sorted(RAW_DIR.glob("*.txt"))
    if not files:
        raise SystemExit(f"No documents found in {RAW_DIR}")
    for path in files:
        meta, body = parse_document(path)
        chunks = chunk_paragraphs(body)
        for i, chunk_text in enumerate(chunks):
            assert len(chunk_text) > 0, "empty chunk produced"
            all_chunks.append({
                "id": f"{path.stem}__chunk{i:02d}",
                "text": chunk_text,
                "metadata": {
                    "source_file": meta.get("source_file", path.name),
                    "title": meta.get("title", ""),
                    "url": meta.get("url", ""),
                    "date": meta.get("date", ""),
                    "doc_type": meta.get("source", ""),
                    "chunk_index": i,
                },
            })
        print(f"{path.name}: {len(chunks)} chunks "
              f"(sizes {min(map(len, chunks))}-{max(map(len, chunks))} chars)")
    OUT_PATH.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nTotal: {len(all_chunks)} chunks from {len(files)} documents -> {OUT_PATH.name}")


if __name__ == "__main__":
    main()
