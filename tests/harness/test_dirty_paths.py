"""dirty_paths: what stops a run (everything uncommitted except runs/ and .cache/)."""
import pytest

from conftest import ROOT  # noqa: F401


@pytest.mark.parametrize("status,expected", [
    (" M runs/kept.json", []),                                  # the leading space of a first line is stripped by git()
    (" M harness/gate.py", ["harness/gate.py"]),
    ("?? packs/quillon-practice/eval/x.jsonl", ["packs/quillon-practice/eval/x.jsonl"]),
    (" M .github/workflows/ci.yml\n M runs/kept.json", [".github/workflows/ci.yml"]),
])
def test_dirty_paths_ignores_runs_and_keeps_the_first_name_whole(monkeypatch, status, expected):
    from harness import run
    monkeypatch.setattr(run, "git", lambda *a, **k: status.strip())
    assert run.dirty_paths() == expected
