"""Retrieval, context expansion and assembly, in the three evidence stages the contract names:

1. ranked hits: the chunks the retriever returns, rank order (each one passed through the access check when it is on);
2. expanded evidence: neighbours, section parents and linked documents added to the hits, one expansion kind at a time;
3. delivered text: ranked hits first, then expansions in rank order, duplicates removed, one global token budget.

The authority rule (conflict groups, applicability, the fixed evaluation date) runs between stages 2 and 3.
"""
from __future__ import annotations

import re
from contextlib import nullcontext
from dataclasses import dataclass, field

from .retrieval.chunkers import HEADING, Chunk
from .retrieval.corpus import TOKEN, count_tokens
from .security.access import item_for_doc

EVAL_DATE = "2026-11-01"
AUTHORITY_RANK = {"wording": 0, "endorsement": 1, "rule": 2, "guide": 3, "brochure": 4, "faq": 4}


@dataclass
class RetrievalResult:
    ranked: list = field(default_factory=list)            # Chunk objects, rank order
    expanded: list = field(default_factory=list)          # Chunk objects added by neighbours, parents, links
    delivered: list = field(default_factory=list)         # Chunk objects the model is given, after dedupe and budget
    delivered_text: str = ""
    delivered_tokens: int = 0
    truncated: bool = False
    conflict: dict | None = None                          # set when documents disagree and no rule picks a winner
    dropped_docs: list = field(default_factory=list)      # documents the authority rule removed
    refused_links: list = field(default_factory=list)     # linked documents the access check refused (link_hop), for the case record

    @property
    def ranked_ids(self): return [c.chunk_id for c in self.ranked]

    @property
    def expanded_ids(self): return [c.chunk_id for c in self.expanded]

    @property
    def delivered_ids(self): return [c.chunk_id for c in self.delivered]

    @property
    def delivered_doc_ids(self): return list(dict.fromkeys(c.doc_id for c in self.delivered))


def _noop(name, **attrs):
    return nullcontext()


def _sections(doc):
    """(start, end, heading) character ranges of a document body, one per heading section."""
    body, marks = doc.body, list(HEADING.finditer(doc.body))
    if not marks:
        return [(0, len(body), doc.title)]
    out = []
    if body[:marks[0].start()].strip():
        out.append((0, marks[0].start(), doc.title))
    for i, m in enumerate(marks):
        out.append((m.start(), marks[i + 1].start() if i + 1 < len(marks) else len(body), m.group(2).strip()))
    return out


def _cut(chunk: Chunk, tokens: int) -> Chunk:
    spans = [m.span() for m in TOKEN.finditer(chunk.text)]
    text = chunk.text[:spans[tokens - 1][1]] if 0 < tokens <= len(spans) else chunk.text
    return Chunk(chunk.chunk_id, chunk.doc_id, chunk.heading, text, count_tokens(text), chunk.position)


def _own_text(chunk: Chunk) -> str:
    """A chunk's text as the document holds it: a heading chunker piece without the heading line put in front of it."""
    text = chunk.text.strip()
    if chunk.heading and text.startswith(chunk.heading + "\n"):
        text = text[len(chunk.heading) + 1:].strip()
    return text


# ---- stage 2: expansions -------------------------------------------------------------------------------------------
def _neighbours(index, hit: Chunk, n: int):
    raise NotImplementedError("YOUR TURN: lab 4 part 1, neighbours, section parent and link hop")


def _section_parent(index, hit: Chunk):
    raise NotImplementedError("YOUR TURN: lab 4 part 1, neighbours, section parent and link hop")


def _linked(index, hit: Chunk, query: str, allow):
    raise NotImplementedError("YOUR TURN: lab 4 part 1, neighbours, section parent and link hop")


# ---- the authority rule ----------------------------------------------------------------------------------------------
def _applicable(meta: dict, query: str, group_products: set) -> bool:
    eff, end = meta.get("effective_from"), meta.get("effective_to")
    if eff and str(eff) > EVAL_DATE:
        return False
    if end and str(end) < EVAL_DATE:
        return False
    ap = meta.get("applies_to")
    if isinstance(ap, dict):
        if ap.get("from") and ap["from"] > EVAL_DATE:
            return False
        if ap.get("to") and ap["to"] < EVAL_DATE:
            return False
        prods = {str(p).lower() for p in (ap.get("product") or []) if str(p).lower() != "all"}
        if prods:
            q = query.lower()
            if any(re.search(rf"\b{re.escape(p)}\b", q) for p in group_products) and not any(re.search(rf"\b{re.escape(p)}\b", q) for p in prods):
                return False
    return True


def _groups(meta: dict) -> set:
    ap = meta.get("applies_to")
    return {str(g).lower() for g in ((ap or {}).get("customer_group") or []) if str(g).lower() != "all"} if isinstance(ap, dict) else set()


def _beats(a: dict, b: dict) -> bool | None:
    """True if document a beats b, False if b beats a, None if no rule picks a winner."""
    if _groups(a) != _groups(b):              # one covers only some customers: who is asking decides, so a person does
        return None
    if a.get("version_chain") == b.get("version_chain") and a.get("owner_scope") == b.get("owner_scope"):
        if b.get("doc_id") and a.get("supersedes") == b["doc_id"]:
            return True
        if a.get("doc_id") and b.get("supersedes") == a["doc_id"]:
            return False
        ea, eb = str(a.get("effective_from") or ""), str(b.get("effective_from") or "")
        if ea != eb:
            return ea > eb
        return None
    ra, rb = AUTHORITY_RANK.get(a.get("authority"), 9), AUTHORITY_RANK.get(b.get("authority"), 9)
    if ra != rb:
        return ra < rb
    return None


def apply_authority(index, doc_ids: list, query: str) -> tuple:
    raise NotImplementedError("YOUR TURN: lab 4 part 2, conflict groups and the authority rule")


# ---- the whole path ------------------------------------------------------------------------------------------------
def _recording(allow, res):
    """The access check for link hops, unchanged, except that a refused link is recorded for the case record."""
    if allow is None:
        return None

    def check(item):
        ok = allow(item)
        if not ok and item.get("kind") == "link" and item.get("doc_id") not in res.refused_links:
            res.refused_links.append(item.get("doc_id"))
        return ok
    return check



def retrieve(index, query: str, principal, settings: dict, allow=None, area_types=None, span=_noop) -> RetrievalResult:
    """`allow(item) -> bool` is the access check bound to the principal, or None when no access defence is on."""
    k = settings["top_k"]
    res = RetrievalResult()

    with span("retrieve", query_tokens=count_tokens(query)):
        depth = max(k * 10, 50) if (allow is not None or area_types) else k
        for chunk, _ in index.search(query, depth):
            meta = index.meta(chunk.doc_id)
            if area_types and meta.get("type") not in area_types:
                continue
            if allow is not None and not allow(item_for_doc(meta, "chunk")):
                continue
            res.ranked.append(chunk)
            if len(res.ranked) == k:
                break

    with span("expand", kind=settings["context"]):
        seen = {c.chunk_id for c in res.ranked}
        mode = settings["context"]
        for hit in res.ranked:
            if mode == "neighbours":
                found, kind = _neighbours(index, hit, settings["neighbours_n"]), "neighbour"
            elif mode == "section_parent":
                found, kind = _section_parent(index, hit), "section"
            elif mode == "link_hop":
                found, kind = _linked(index, hit, query, _recording(allow, res)), "link"
            else:
                break
            for c in found:
                if c.chunk_id in seen:
                    continue
                if allow is not None and kind in ("neighbour", "section") and not allow(item_for_doc(index.meta(c.doc_id), kind)):
                    continue
                seen.add(c.chunk_id)
                res.expanded.append(c)

    with span("assemble", limit=settings["context_token_limit"]):
        candidates = res.ranked + res.expanded
        if settings["authority_rule"] == "on":
            dropped, res.conflict = apply_authority(index, list(dict.fromkeys(c.doc_id for c in candidates)), query)
            res.dropped_docs = sorted(dropped)
            candidates = [c for c in candidates if c.doc_id not in dropped]
        res.delivered = list(candidates)      # starter: no budget, no duplicate check
        res.delivered_text = "\n\n".join(c.text for c in res.delivered)
        res.delivered_tokens = sum(c.tokens for c in res.delivered)
    return res
