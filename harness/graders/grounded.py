"""Grounded: each key fact the reply states also appears (with its qualifiers) in a cited document."""
from .fact import check_fact


def grade_grounded(reply_text: str, key_facts: list, cited_doc_texts: dict) -> dict:
    """`cited_doc_texts` maps a cited document id to its text (stored with the step by the harness).

    A reply that states none of its key facts is not grounded (there is nothing it can be grounded in); the
    answer-success check is what reports the missing facts."""
    stated = [f for f in key_facts if check_fact(reply_text, f)["ok"]]
    per = {f["id"]: any(check_fact(t, f, rivals=False)["ok"] for t in (cited_doc_texts or {}).values()) for f in stated}
    return {"grounded": bool(stated) and all(per.values()), "stated": [f["id"] for f in stated], "per_fact": per}
