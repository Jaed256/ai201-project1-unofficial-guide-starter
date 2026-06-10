"""Evaluation harness: runs the 5 test questions from planning.md end-to-end
and prints everything the README evaluation report needs: question, expected answer,
retrieved chunks (with distances), system response, and a slot for the accuracy judgment.

Accuracy judgments (accurate / partially accurate / inaccurate) are made by Jaed,
not auto-assigned — that's the intellectual work of the evaluation.
"""
import json
from pathlib import Path

from rag import retrieve, generate

QUESTIONS_PATH = Path(__file__).parent / "eval_questions.json"
OUT_PATH = Path(__file__).parent / "eval_results.json"


def main():
    if not QUESTIONS_PATH.exists():
        raise SystemExit(
            "Create eval_questions.json first — a list of "
            '{"question": ..., "expected": ...} objects (your 5 from planning.md).'
        )
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    results = []
    for i, q in enumerate(questions, 1):
        print("=" * 70)
        print(f"Q{i}: {q['question']}")
        print(f"EXPECTED: {q['expected']}\n")
        out = generate(q["question"])
        print("RETRIEVED:")
        for c in out["chunks"]:
            print(f"  [{c['distance']}] {c['metadata']['source_file']} :: {c['text'][:100]}...")
        print(f"\nRESPONSE: {out['answer']}\n")
        results.append({
            "question": q["question"],
            "expected": q["expected"],
            "response": out["answer"],
            "retrieved": [
                {"source": c["metadata"]["source_file"], "distance": c["distance"],
                 "preview": c["text"][:150]}
                for c in out["chunks"]
            ],
            "judgment": "TODO — Jaed: accurate / partially accurate / inaccurate + why",
        })
    OUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT_PATH.name} — fill in your accuracy judgments there or in the README.")


if __name__ == "__main__":
    main()
