"""Access checks. `allowed(item, principal)` is asked about every item that could reach the model or the user:
ranked hits, neighbours, section parents, linked documents, history, tool results and handoff notes.

An item is a dict. Documents carry `audience` and `owner_scope`; history carries `principal_id`; tool results carry
`account_id` (and `verified_account` when identity was proved by a policy number and date of birth); a note carries
the `items` it was built from. Anything of an unknown kind is refused.
"""
from __future__ import annotations


def item_for_doc(meta: dict, kind: str = "chunk") -> dict:
    return {"kind": kind, "doc_id": meta.get("doc_id"), "audience": meta.get("audience", "public"),
            "owner_scope": meta.get("owner_scope", "everyone")}


def allowed(item: dict, principal) -> bool:
    # SHIPPED STUB until lab 7: the starter body is `return True`, so the baseline leaks internal documents.
    return True
