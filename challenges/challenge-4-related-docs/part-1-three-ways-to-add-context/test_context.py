"""Lab 4, part 1: neighbours, section parent, one link hop and assembly under one budget.
A three-document pack is written into a temporary folder. No model, no real pack, no reference numbers."""
from pathlib import Path

import pytest

from app import context
from app.core import Agent
from app.retrieval.index import Index
from app.types import Principal

ALPHA = """# Alpha

## Refunds
refund requests need the order number. refund requests are answered within five days. refund money returns to the card.

## Shipping
shipping takes three days. shipping is free over fifty dollars. express shipping costs more than standard shipping."""
BETA = "Beta guide. Warranty covers faults for two years. Warranty claims need the receipt."
GAMMA = "Gamma note. Warranty gamma rays and nothing else. Warranty gamma is a different thing."
DOCS = {"doc-alpha": ("Alpha", ALPHA, ["doc-beta"]), "doc-beta": ("Beta", BETA, ["doc-gamma"]), "doc-gamma": ("Gamma", GAMMA, [])}

ASKER = Principal("p-test", "customer", True, None)


def settings(**over):
    s = {"chunker": "fixed", "chunk_size": 14, "overlap": 0, "retriever": "bm25", "top_k": 1, "context": "none", "neighbours_n": 1,
         "context_token_limit": 3000, "authority_rule": "off", "embed_model": "nomic-embed-text"}
    s.update(over)
    return s


@pytest.fixture
def pack(tmp_path):
    (tmp_path / "corpus").mkdir()
    for doc_id, (title, body, links) in DOCS.items():
        front = f"doc_id: {doc_id}\ntitle: {title}\naudience: public\nowner_scope: everyone\nlinks: {links}\n"
        (tmp_path / "corpus" / f"{doc_id}.md").write_text(f"---\n{front}---\n{body}\n", encoding="utf-8")
    return tmp_path


def run(pack, query, allow=None, **over):
    s = settings(**over)
    return context.retrieve(Index(pack, s), query, ASKER, s, allow)


def test_neighbours_stop_at_the_edge_of_the_document(pack):
    index = Index(pack, settings(chunk_size=10))
    chunks = index.by_doc["doc-alpha"]
    assert len(chunks) >= 5, "the fixture document must be long enough to have an inside"
    first, middle, last = chunks[0], chunks[2], chunks[-1]
    assert [c.chunk_id for c in context._neighbours(index, first, 1)] == [chunks[1].chunk_id]       # nothing before the first chunk
    assert [c.chunk_id for c in context._neighbours(index, last, 1)] == [chunks[-2].chunk_id]       # nothing after the last chunk
    assert {c.chunk_id for c in context._neighbours(index, middle, 1)} == {chunks[1].chunk_id, chunks[3].chunk_id}
    two = {c.chunk_id for c in context._neighbours(index, middle, 2)}
    assert two == {c.chunk_id for c in (chunks[0], chunks[1], chunks[3], chunks[4])}
    assert all(c.doc_id == "doc-alpha" for c in context._neighbours(index, middle, 2))              # never a chunk of another document


def test_the_section_parent_is_the_whole_heading_section(pack):
    index = Index(pack, settings(chunk_size=8))
    hit = next(c for c in index.by_doc["doc-alpha"] if "refund money returns" in c.text)           # a small chunk inside the Refunds section
    (parent,) = context._section_parent(index, hit)
    assert parent.heading == "Refunds" and parent.doc_id == "doc-alpha"
    assert "order number" in parent.text and "refund money returns to the card" in parent.text      # the section from its first line to its last
    assert "shipping" not in parent.text.lower()                                                   # and none of the next section
    assert parent.chunk_id not in {c.chunk_id for c in index.by_doc["doc-alpha"]}                  # it is a new piece of evidence, with its own id


def test_assembly_orders_hits_first_removes_duplicates_and_applies_one_budget(pack):
    res = run(pack, "refund requests", context="neighbours", top_k=2)
    ranked, expanded, delivered = res.ranked_ids, res.expanded_ids, res.delivered_ids
    assert len(ranked) == 2 and expanded
    assert delivered[:2] == ranked                                                                 # ranked hits come first
    assert delivered[2:] == [c for c in expanded if c not in ranked]                               # then expansions, in the order they were found
    assert len(delivered) == len(set(delivered))                                                  # no chunk twice
    assert not set(ranked) & set(expanded)                                                         # a hit that is also a neighbour is not repeated
    assert not res.truncated

    limit = 20                                                                                     # one global limit on the delivered text
    cut = run(pack, "refund requests", context="neighbours", top_k=2, context_token_limit=limit)
    assert cut.truncated is True                                                                   # the cut is logged
    assert cut.delivered_tokens <= limit
    assert cut.delivered_ids[0] == ranked[0]                                                       # what survives is what ranked first
    assert cut.delivered_tokens == context.count_tokens(cut.delivered_text.replace("\n\n", " "))


def test_a_citation_is_valid_only_for_a_delivered_document(pack):
    res = run(pack, "refund requests", context="link_hop", top_k=1)
    delivered = set(res.delivered_doc_ids)
    assert {"doc-alpha", "doc-beta"} <= delivered                                                  # the linked document was delivered
    reply = "Refunds take five days [doc-alpha]. Faults are covered for two years [doc-beta]. Rays [doc-gamma]."
    assert Agent.parse_citations(None, reply, delivered) == ["doc-alpha", "doc-beta"]              # doc-gamma was never delivered
    parent = run(pack, "refund requests", context="section_parent", top_k=1, chunk_size=8)
    assert Agent.parse_citations(None, "[doc-alpha]", set(parent.delivered_doc_ids)) == ["doc-alpha"]


def test_the_hop_asks_allowed_for_each_target_and_drops_a_refused_one(pack):
    asked = []

    def deny_links(item):
        asked.append(item)
        return item["kind"] != "link"                                                              # hits are allowed, linked documents are not

    refused = run(pack, "refund requests", allow=deny_links, context="link_hop", top_k=1)
    links = [i for i in asked if i["kind"] == "link"]
    assert [i["doc_id"] for i in links] == ["doc-beta"]                                            # asked once, for the one target of the hit's document
    assert "doc-beta" not in refused.delivered_doc_ids and refused.expanded == []                  # refused: not delivered, not even expanded

    allowed = run(pack, "refund requests", allow=lambda item: True, context="link_hop", top_k=1)
    assert "doc-beta" in allowed.delivered_doc_ids


def test_the_hop_follows_one_level_only(pack):
    res = run(pack, "refund requests", context="link_hop", top_k=1)
    docs = set(res.delivered_doc_ids)
    assert "doc-beta" in docs                                                                      # alpha links to beta
    assert "doc-gamma" not in docs                                                                 # beta links to gamma: a second hop, not followed
