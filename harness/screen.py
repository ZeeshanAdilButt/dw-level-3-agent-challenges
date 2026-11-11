"""Retrieval-only screening: no chat model. Exact and fast, so it reports changes, not verdicts.

    python -m harness.screen --pack quillon --chunker fixed --size 400 --retriever bm25 [--label x]

The functions here (screen, summarise, fact_present) are the lab 3 facts script's reference numbers
(tools/lab3_facts.py) and stay as they are. The command itself lives in harness/screening.py.
"""
import json
from collections import defaultdict
from pathlib import Path

from app.retrieval.chunkers import chunk_corpus
from app.retrieval.corpus import load_corpus

ROOT = Path(__file__).resolve().parent.parent


def make_retriever(name, chunks):
    if name == "bm25":
        from app.retrieval.bm25 import BM25
        return BM25(chunks)
    if name == "trigram":
        from app.retrieval.trigram import Trigram
        return Trigram(chunks)
    if name == "vector":
        from app.retrieval.vectors import Vectors
        return Vectors(chunks)
    if name == "hybrid":
        from app.retrieval.bm25 import BM25
        from app.retrieval.fusion import Hybrid
        from app.retrieval.vectors import Vectors
        return Hybrid(BM25(chunks), Vectors(chunks))
    raise ValueError(name)


def fact_present(text, fact):
    low = text.lower()
    return any(str(f).lower() in low for f in fact["forms"])


def screen(pack, chunker, size, overlap, retriever, k=5):
    pack_dir = ROOT / "packs" / pack
    docs = load_corpus(pack_dir)
    chunks = chunk_corpus(docs, chunker, size, overlap)
    r = make_retriever(retriever, chunks)
    questions = [json.loads(l) for l in open(pack_dir / "eval" / "questions.jsonl", encoding="utf-8")]
    cases = []
    for q in questions:
        if "retrieval" not in (q.get("needs") or []) or not q.get("gold_sources"):
            continue
        query = q["turns"][-1]
        hits = r.search(query, k)
        ids = [h[0].doc_id for h in hits]
        gold = set(q["gold_sources"])
        uniq = lambda n: len(gold & set(ids[:n])) / len(gold)
        rank = next((i + 1 for i, d in enumerate(ids) if d in gold), None)
        context = "\n\n".join(h[0].text for h in hits)
        kf = q.get("key_facts") or []
        cases.append({
            "id": q["id"], "slices": q.get("slices") or [], "retrieved": [h[0].chunk_id for h in hits],
            "recall3": uniq(3), "recall5": uniq(5), "rr": 1 / rank if rank else 0.0,
            "fact_recall": (sum(fact_present(context, f) for f in kf) / len(kf)) if kf else None,
            "context_tokens": sum(h[0].tokens for h in hits),
        })
    return chunks, cases


def summarise(cases):
    def agg(rows):
        fr = [c["fact_recall"] for c in rows if c["fact_recall"] is not None]
        return {"n": len(rows),
                "recall3": round(sum(c["recall3"] for c in rows) / len(rows), 3),
                "recall5": round(sum(c["recall5"] for c in rows) / len(rows), 3),
                "mrr": round(sum(c["rr"] for c in rows) / len(rows), 3),
                "fact_recall": round(sum(fr) / len(fr), 3) if fr else None,
                "context_tokens": round(sum(c["context_tokens"] for c in rows) / len(rows))}
    by = defaultdict(list)
    for c in cases:
        for s in c["slices"]:
            by[s].append(c)
    return agg(cases), {s: agg(v) for s, v in sorted(by.items())}


def main():
    """`python -m harness.screen` is kept as an alias of `python -m harness screen` (records are immutable now)."""
    from .screening import main as screening_main
    return screening_main()


if __name__ == "__main__":
    raise SystemExit(main())
