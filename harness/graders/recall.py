"""Recall at k, MRR and evidence-span coverage, all on stored chunk ids (decision C6: ranked hits, delivered text).

`offsets` maps a chunk id to [doc_id, start, end] (end exclusive) in the document's canonical text, stored with
the step by the harness. A gold span is {"doc", "start", "end"}.
"""
from .citation import doc_of

def recall_at(ranked_ids: list, gold_docs: list, k: int) -> float:
    raise NotImplementedError("YOUR TURN: lab 1, 1.6: write recall at k (unique gold documents in the top k, per question)")

def _overlaps(off, span) -> bool:
    return bool(off) and off[0] == span["doc"] and off[1] < span["end"] and span["start"] < off[2]


def _covers(off, span) -> bool:
    return bool(off) and off[0] == span["doc"] and off[1] <= span["start"] and off[2] >= span["end"]


def reciprocal_rank(ranked_ids: list, gold_docs: list, gold_spans: list, offsets: dict) -> float:
    """1 / rank of the first ranked chunk that overlaps a gold span; with no spans, of the first chunk of a gold
    document. 0 when none of the ranked chunks qualifies."""
    for i, cid in enumerate(ranked_ids or [], start=1):
        if gold_spans:
            if any(_overlaps((offsets or {}).get(cid), s) for s in gold_spans):
                return 1 / i
        elif doc_of(cid) in set(gold_docs or []):
            return 1 / i
    return 0.0


def span_coverage(delivered_ids: list, gold_spans: list, offsets: dict) -> tuple:
    """Return (covered, total): gold spans that lie fully inside one delivered chunk."""
    covered = sum(1 for s in gold_spans or [] if any(_covers((offsets or {}).get(c), s) for c in delivered_ids or []))
    return covered, len(gold_spans or [])

