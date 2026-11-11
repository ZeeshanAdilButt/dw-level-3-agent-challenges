"""Lab 1, part 3: graders, records, three runs. Fixed fixture replies only: no model, no reference numbers.

Invariant (passes on the starter): test_validate_sample.
Acceptance (fails on the starter): test_fact_grader, test_citation_grader, test_recall_grader (each with
    NotImplementedError: YOUR TURN: ...) and test_prediction_first (AssertionError: no prediction commit before the first run record).
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "challenges" / "_shared"))

from panel_render import is_reference_tree  # noqa: E402

# The graders are imported inside each test: on the starter their modules raise NotImplementedError when imported,
# and the invariant tests (the sample record, the checkers) must still run.

PRO = {"id": "f-pro", "entity": "Pro plan", "forms": ["$38", "38 dollars"], "qualifiers": ["per month", "monthly"],
       "rival_forms": [["$45", "45 dollars"]]}


def verdict(text, fact=PRO):
    from harness.graders.fact import check_fact
    return check_fact(text, fact)


# ---- the fact grader: one pass and one trap at a time -------------------------------------------------------------

def test_fact_grader():
    assert verdict("The Pro plan costs $38 per seat per month.")["ok"]
    assert verdict("pro PLAN is 38 dollars monthly.")["ok"]                                   # another accepted form
    # trap: a number tied to the wrong entity
    assert verdict("The Team plan costs $38 per seat per month.")["reason"] == "entity"
    # trap: a negated fact
    assert verdict("The Pro plan does not cost $38 per month.")["reason"] == "negated"
    # trap: the value and the entity sit in different sentences
    assert not verdict("Prices are on the sheet. The Pro plan is a popular choice. It costs $38 per month.")["ok"]
    # trap: a missing qualifier ("per year" for a monthly price)
    assert verdict("The Pro plan costs $38 per seat per year.")["reason"] == "qualifier"
    # trap: a different value for the same attribute and entity
    assert verdict("The Pro plan costs $38 per seat per month. The Pro plan costs $45 per seat per month.")["reason"] == "rival"
    # a comparison that states the right value and the rival in one sentence is allowed
    assert verdict("The Pro plan costs $38 per seat per month, not $45 per seat per month.")["ok"] is False   # negation cue
    assert verdict("The Pro plan costs $38 per seat per month, while a rival charges $45 per month.")["ok"]
    # trap: a number inside a longer number is not the value
    assert verdict("The Pro plan costs $380 per seat per month.")["reason"] == "missing"
    # no qualifiers on the fact means none are needed
    from harness.graders.fact import check_fact
    assert check_fact("Pro support replies within 4 business hours.",
                      {"id": "f", "entity": "Pro support", "forms": ["4 business hours"]})["ok"]


def test_citation_grader():
    from harness.graders.citation import grade_citations
    delivered = {"doc-a", "doc-b"}
    ok = grade_citations(["doc-a"], delivered, ["doc-a"])
    assert ok["cited_correctly"] and ok["valid"] == ["doc-a"] and ok["precision_num"] == 1 and ok["precision_den"] == 1
    # trap: a cited id that was not delivered to the model
    bad = grade_citations(["doc-a", "doc-z"], delivered, ["doc-a"])
    assert bad["invalid"] == ["doc-z"] and not bad["cited_correctly"] and bad["gold_cited"]
    # a delivered document that is not gold is valid but not correct
    other = grade_citations(["doc-b"], delivered, ["doc-a"])
    assert other["valid"] == ["doc-b"] and not other["gold_cited"] and not other["cited_correctly"]
    # no citation is never correct
    none = grade_citations([], delivered, ["doc-a"])
    assert not none["cited_correctly"] and none["precision_den"] == 0
    # one document cited twice counts once
    twice = grade_citations(["doc-a", "doc-a"], delivered, ["doc-a"])
    assert twice["cited"] == ["doc-a"] and twice["precision_den"] == 1


def test_recall_grader():
    from harness.graders.recall import recall_at
    ranked = ["doc-a#0", "doc-a#1", "doc-b#0", "doc-c#0"]
    # trap: two chunks of one document count once
    assert recall_at(ranked, ["doc-a", "doc-b"], 2) == 0.5
    assert recall_at(ranked, ["doc-a", "doc-b"], 3) == 1.0
    assert recall_at(ranked, ["doc-c"], 3) == 0.0                  # past the cut-off
    assert recall_at(ranked, ["doc-c"], 4) == 1.0
    assert recall_at([], ["doc-a"], 5) == 0.0
    assert recall_at(ranked, [], 5) == 0.0                         # nothing to find: no score, never 1


# ---- the prediction comes before the first record ------------------------------------------------------------------

def prediction_problem(records: list):
    """None when the first full-run record names a prediction commit made before it started; else the problem."""
    runs = sorted((r for r in records if r.get("kind") == "run"), key=lambda r: r.get("started_at", ""))
    if not runs:
        return "no run record yet"
    first = runs[0]
    if not first.get("prediction_commit") or not first.get("prediction_committed_at"):
        return "no prediction commit before the first run record"
    if first["prediction_committed_at"] > first["started_at"]:
        return "the prediction was committed after the first run record started"
    return None


def test_the_prediction_checker_on_fixed_records():
    ok = {"kind": "run", "started_at": "2026-11-08T10:00:00+00:00", "prediction_commit": "abc", "prediction_committed_at": "2026-11-08T09:00:00+00:00"}
    assert prediction_problem([ok]) is None
    assert prediction_problem([dict(ok, prediction_commit=None)]) == "no prediction commit before the first run record"
    assert "after" in prediction_problem([dict(ok, prediction_committed_at="2026-11-08T11:00:00+00:00")])
    assert prediction_problem([]) == "no run record yet"


@pytest.mark.skipif(is_reference_tree(), reason="the reference tree has no learner prediction commit; the checker is tested above")
def test_prediction_first():
    from harness.records import all_runs
    problem = prediction_problem(all_runs())
    assert problem is None, problem if problem != "no run record yet" else "no prediction commit before the first run record"
    written = ROOT / "predictions" / "lab1-noise.md"
    assert written.exists() and written.read_text(encoding="utf-8").strip(), "predictions/lab1-noise.md is missing or empty"


# ---- invariant ---------------------------------------------------------------------------------------------------

def test_validate_sample():
    """The shipped validator accepts the shipped sample record (part 3 folder, sample-record/runs/r000)."""
    old = os.environ.get("DW_ROOT")
    os.environ["DW_ROOT"] = str(HERE / "sample-record")
    try:
        from harness.schema import validate_run_dir
        assert validate_run_dir("r000") == []
    finally:
        if old is None:
            del os.environ["DW_ROOT"]
        else:
            os.environ["DW_ROOT"] = old
