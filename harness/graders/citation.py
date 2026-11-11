"""Citation grader. A citation is valid when its document is in the delivered evidence (stage 3, decision C6)."""


def doc_of(chunk_id: str) -> str:
    return str(chunk_id).rsplit("#", 1)[0]


def delivered_docs(ev: dict) -> set:
    """Documents the model was given: the delivered doc ids plus the documents of the delivered chunk ids."""
    ev = ev or {}
    return set(ev.get("delivered_doc_ids") or []) | {doc_of(c) for c in ev.get("delivered_evidence_ids") or []}


def grade_citations(citations: list, delivered: set, gold_sources: list) -> dict:
    raise NotImplementedError("YOUR TURN: lab 1, 1.6: write the citation grader (valid if delivered; precision against gold sources)")
