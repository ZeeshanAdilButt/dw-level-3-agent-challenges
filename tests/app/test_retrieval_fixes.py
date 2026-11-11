"""Retrieval fixes: the embed model setting reaches the embedder, a heading piece stays within its limit, the section
parent of a heading chunk is its own section, and a section parent replaces the hit it holds instead of repeating it."""
from types import SimpleNamespace

import pytest

from app import context
from app.retrieval import vectors
from app.retrieval.chunkers import by_heading
from app.retrieval.corpus import count_tokens
from app.retrieval.index import Index
from app.types import Principal

ASKER = Principal("p-test", "customer", True, None)
BODY = ("# Alpha\n\n## Refunds\n" + " ".join(f"refund{i}" for i in range(30)) +
        "\n\n## Shipping\nshipping takes three days. shipping is free over fifty dollars.")


def settings(**over):
    s = {"chunker": "heading", "chunk_size": 16, "overlap": 0, "retriever": "bm25", "top_k": 1, "context": "none",
         "neighbours_n": 1, "context_token_limit": 3000, "authority_rule": "off", "embed_model": "nomic-embed-text"}
    s.update(over)
    return s


@pytest.fixture
def pack(tmp_path):
    (tmp_path / "corpus").mkdir()
    front = "doc_id: doc-alpha\ntitle: Alpha\naudience: public\nowner_scope: everyone\nlinks: []\n"
    (tmp_path / "corpus" / "doc-alpha.md").write_text(f"---\n{front}---\n{BODY}\n", encoding="utf-8")
    return tmp_path


def test_the_embed_model_setting_reaches_every_embedding_call(pack, monkeypatch):
    seen = []

    def fake_embed(texts, prefix, model=None):
        seen.append(model)
        return [[1.0, float(len(t) % 3)] for t in texts]

    monkeypatch.setattr(vectors, "embed", fake_embed)
    index = Index(pack, settings(chunker="fixed", chunk_size=400, retriever="vector", embed_model="mxbai-embed-large"))
    index.search("refund", 1)
    assert seen and set(seen) == {"mxbai-embed-large"}
    assert vectors._key("p: ", "t", "mxbai-embed-large") != vectors._key("p: ", "t", "nomic-embed-text")   # one cache entry per model


def test_a_heading_piece_with_its_heading_put_in_front_stays_within_the_limit():
    doc = SimpleNamespace(doc_id="doc-x", title="X", body="## Limits and allowances\n\n" + " ".join(f"t{i}" for i in range(60)))
    pieces = by_heading(doc, 10)
    assert len(pieces) >= 6 and all(p.tokens <= 10 for p in pieces)
    assert all("Limits and allowances" in p.text for p in pieces) and "t59" in pieces[-1].text


def test_the_section_parent_of_a_continued_heading_chunk_is_its_own_section(pack):
    index = Index(pack, settings())
    chunks = index.by_doc["doc-alpha"]
    shipping = next(c for c in chunks if c.heading == "Shipping")
    later_refund = [c for c in chunks if c.heading == "Refunds"][-1]       # a continuation piece: its heading was put in front
    assert not later_refund.text.startswith("#")
    (parent,) = context._section_parent(index, later_refund)
    assert parent.heading == "Refunds" and "refund29" in parent.text and "shipping" not in parent.text
    assert context._section_parent(index, shipping) == []                  # the whole section already: nothing to add


def test_a_section_parent_replaces_the_hit_it_holds_and_counts_its_tokens_once(pack):
    s = settings(chunker="fixed", chunk_size=8, context="section_parent")
    res = context.retrieve(Index(pack, s), "refund3", ASKER, s)
    (hit,) = res.ranked
    (parent,) = res.expanded
    assert hit.text.strip() in parent.text
    assert res.delivered_ids == [parent.chunk_id]                           # the enclosing section, once
    assert res.delivered_text.count(hit.text.strip()) == 1
    assert res.delivered_tokens == parent.tokens == count_tokens(res.delivered_text.replace("\n\n", " "))


def test_a_delivered_section_parent_has_offsets_for_span_coverage(pack):
    from harness.retrieval_bridge import offsets_table
    docs, table = offsets_table(settings(chunker="fixed", chunk_size=8), pack)
    body = docs["doc-alpha"].body
    index = Index(pack, settings(chunker="fixed", chunk_size=8))
    for k, (s, e, _) in enumerate(context._sections(index.docs["doc-alpha"])):
        doc, start, end = table[f"doc-alpha#sec{k}"]
        assert doc == "doc-alpha" and body[start:end] == body[s:e].strip()
