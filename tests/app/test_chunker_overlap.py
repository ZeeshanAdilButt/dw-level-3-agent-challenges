from types import SimpleNamespace

import pytest

from app.retrieval.chunkers import chunk_by_heading, by_heading, chunk_with_overlap, fixed


def doc(body):
    return SimpleNamespace(doc_id="d", title="T", body=body)


def test_overlap_chunks_share_exactly_the_overlap():
    assert [c.text for c in fixed(doc("a b c d e f g h"), 4, 2)] == ["a b c d", "c d e f", "e f g h"]
    assert fixed(doc(""), 4, 0) == [] and len(fixed(doc("a b"), 4, 1)) == 1


@pytest.mark.parametrize("overlap", [-1, 4, 5])
def test_overlap_outside_zero_to_size_is_an_error(overlap):
    with pytest.raises(ValueError):
        fixed(doc("a b c d e f"), 4, overlap)
    with pytest.raises(ValueError):
        chunk_with_overlap(doc("a b c d e f"), 4, overlap)


def test_spec_names_are_the_same_functions():
    assert chunk_by_heading is by_heading
