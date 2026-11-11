"""Lab 3, part 1: the three retrievers you write. Fixed inputs only: no model, no pack, no reference numbers."""
import pytest

from app.retrieval import vectors
from app.retrieval.chunkers import Chunk
from app.retrieval.fusion import Hybrid
from app.retrieval.trigram import Trigram, trigrams


def chunk(chunk_id, text):
    return Chunk(chunk_id, chunk_id.split("#")[0], "title", text, len(text.split()), 0)


def test_trigram():
    # The padding rule: two spaces before a word, one after, then every piece of three characters.
    assert trigrams("refund") == {"  r", " re", "ref", "efu", "fun", "und", "nd "}
    # NFKC and lowercase: a full-width letter and a capital give the same pieces as the plain word.
    assert trigrams("REFUND") == trigrams("refund") == trigrams("\uff52\uff45\uff46\uff55\uff4e\uff44")
    # Words are letters and digits; punctuation only separates them.
    assert trigrams("re-fund") == trigrams("re fund")

    index = Trigram([chunk("doc-a#0", "refunds"), chunk("doc-b#0", "price")])
    hits = index.search("refund", k=5)
    assert [(c.chunk_id, round(s, 3)) for c, s in hits] == [("doc-a#0", 0.667)]    # 6 shared pieces of 9 in all; "price" scores 0 and is left out

    # Ties: equal score, smallest chunk id as text first. "doc-10#0" sorts before "doc-2#0" as text.
    tied = Trigram([chunk("doc-2#0", "refund"), chunk("doc-10#0", "refund"), chunk("doc-1#0", "refund")])
    assert [c.chunk_id for c, _ in tied.search("refund", k=2)] == ["doc-1#0", "doc-10#0"]

    assert index.search("???", k=5) == []                                           # a question with no words matches nothing


class Fixed:
    """A retriever that returns a fixed list and remembers how many results it was asked for."""

    def __init__(self, ids):
        self.ids = ids
        self.asked = None

    def search(self, query, k=5):
        self.asked = k
        return [(chunk(i, i), 1.0 / n) for n, i in enumerate(self.ids[:k], start=1)]


def test_fusion():
    # The two lists from chapter 3.4: a is first in one list and second in the other.
    first = Fixed(["doc-a#0", "doc-b#0", "doc-c#0"])
    second = Fixed(["doc-b#0", "doc-a#0", "doc-d#0"])
    hits = Hybrid(first, second).search("anything", k=4)
    scores = {c.chunk_id: s for c, s in hits}
    assert scores["doc-a#0"] == pytest.approx(1 / 61 + 1 / 62)
    assert scores["doc-b#0"] == pytest.approx(1 / 62 + 1 / 61)
    assert scores["doc-c#0"] == pytest.approx(1 / 63)                                # in one list only: nothing from the other
    assert scores["doc-d#0"] == pytest.approx(1 / 63)
    # a and b tie on score and c and d tie on score: the smaller chunk id as text comes first.
    assert [c.chunk_id for c, _ in hits] == ["doc-a#0", "doc-b#0", "doc-c#0", "doc-d#0"]
    # Each list is asked for its top 20, whatever k is, and k only cuts the fused list.
    assert first.asked == 20 and second.asked == 20
    assert len(Hybrid(first, second).search("anything", k=2)) == 2

    # Chunk X is first in one list and 20th in the other; chunk Y is second in both. Y wins.
    pad_one = [f"doc-p{i:02d}#0" for i in range(18)]
    pad_two = [f"doc-q{i:02d}#0" for i in range(17)]
    one = Fixed(["doc-x#0", "doc-y#0"] + pad_one)
    other = Fixed(["doc-z#0", "doc-y#0"] + pad_two + ["doc-x#0"])
    scores = {c.chunk_id: s for c, s in Hybrid(one, other).search("q", k=60)}
    assert scores["doc-x#0"] == pytest.approx(1 / 61 + 1 / 80)
    assert scores["doc-y#0"] == pytest.approx(1 / 62 + 1 / 62)
    assert scores["doc-y#0"] > scores["doc-x#0"]


def test_vectors(monkeypatch):
    # Three fixed document vectors and one fixed question vector. embed() is replaced, so no model runs.
    docs = {"alpha": [3.0, 0.0], "beta": [0.0, 5.0], "gamma": [1.0, 1.0]}
    query_vec = [2.0, 1.0]
    seen = []

    def fake_embed(texts, prefix, model=None):
        seen.append((prefix, list(texts)))
        return [list(query_vec) if prefix == "search_query: " else list(docs[t]) for t in texts]

    monkeypatch.setattr(vectors, "embed", fake_embed)
    chunks = [chunk("doc-1#0", "alpha"), chunk("doc-2#0", "beta"), chunk("doc-3#0", "gamma")]
    index = vectors.Vectors(chunks)
    hits = index.search("question", k=3)
    # Cosine similarity: gamma about 0.949, alpha about 0.894, beta about 0.447. Length does not matter: beta is the longest vector.
    assert [c.chunk_id for c, _ in hits] == ["doc-3#0", "doc-1#0", "doc-2#0"]
    assert [round(s, 3) for _, s in hits] == [0.949, 0.894, 0.447]
    assert len(index.search("question", k=2)) == 2
    # Documents are embedded with one prefix and questions with the other.
    assert ("search_document: ", ["alpha", "beta", "gamma"]) in seen
    assert ("search_query: ", ["question"]) in seen

    # Ties: two chunks with the same vector are ordered by chunk id as text.
    docs.update({"twin-a": [1.0, 0.0], "twin-b": [1.0, 0.0]})
    twins = vectors.Vectors([chunk("doc-9#0", "twin-a"), chunk("doc-10#0", "twin-b")])
    assert [c.chunk_id for c, _ in twins.search("question", k=2)] == ["doc-10#0", "doc-9#0"]
