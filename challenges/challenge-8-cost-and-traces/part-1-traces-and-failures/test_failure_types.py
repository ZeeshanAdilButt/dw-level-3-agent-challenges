"""Lab 8, part 1: failures by type. Twelve hand-made cases, one per type, then the failures panel on fixed data.

`failure_type(spec, verdict)` in harness/graders/case.py is shipped. The panel in dashboard/panels/failures.js is yours.
Fixed inputs only; no run records and no reference numbers.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
for p in (ROOT, ROOT / "challenges" / "challenge-8-cost-and-traces"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from panel_helper import needs_node, render_panel  # noqa: E402

from harness.graders.case import FAILURE_ORDER, failure_type  # noqa: E402

GOLD = {"gold_sources": ["doc-pricing-table"]}
ANSWERED = {"kind": "question", "expected_action": "answer", "observed_action": "answer"}

# type -> (spec, verdict) built by hand: only the fields that decide that type are set
CASES = {
    "timeout": ({}, {"timeout": True}),
    "hard_rule_broken": ({}, {**ANSWERED, "must_pass": True}),
    "leak": ({}, {**ANSWERED, "leaks": ["canary Otter-7 in the reply"]}),
    "injection_followed": ({"family": "doc-injection", "pass_rule": {"type": "no_tool"}}, {"kind": "attack"}),
    "missed_handoff": ({}, {"kind": "question", "expected_action": "handoff", "observed_action": "answer"}),
    "false_handoff": ({}, {"kind": "question", "expected_action": "answer", "observed_action": "handoff"}),
    "wrong_action": ({}, {**ANSWERED, "action_ok": False}),
    "tool_error": ({}, {"kind": "question", "expected_action": "tool", "observed_action": "tool", "tool": {"ok": False}}),
    "over_refusal": ({}, {"kind": "question", "expected_action": "answer", "observed_action": "refuse"}),
    "retrieval_miss": (GOLD, {**ANSWERED, "facts": {"f-pro": "missing"}, "context_facts": {"f-pro": False}}),
    "wrong_fact": (GOLD, {**ANSWERED, "facts": {"f-pro": "wrong"}, "context_facts": {"f-pro": True}}),
    "no_citation": (GOLD, {**ANSWERED, "facts": {"f-pro": "ok"}, "citations": {"cited_correctly": False}}),
}


def test_there_is_one_hand_made_case_for_each_of_the_twelve_types():
    assert set(CASES) == set(FAILURE_ORDER) and len(FAILURE_ORDER) == 12


@pytest.mark.parametrize("name", FAILURE_ORDER)
def test_each_case_gets_its_own_type(name):
    spec, verdict = CASES[name]
    assert failure_type(spec, verdict) == name


def test_the_first_matching_type_wins():
    leaks_and_wrong = {**ANSWERED, "leaks": ["canary"], "facts": {"f-pro": "wrong"}, "context_facts": {"f-pro": True}}
    assert failure_type(GOLD, leaks_and_wrong) == "leak"                      # leak comes before wrong_fact
    timed_out_and_leaks = {**leaks_and_wrong, "timeout": True}
    assert failure_type(GOLD, timed_out_and_leaks) == "timeout"               # and timeout comes before both
    assert FAILURE_ORDER.index("leak") < FAILURE_ORDER.index("wrong_fact")


def test_a_case_with_nothing_wrong_has_no_type():
    assert failure_type(GOLD, {**ANSWERED, "facts": {"f-pro": "ok"}, "citations": {"cited_correctly": True}}) is None


@needs_node
def test_the_failures_panel_counts_each_failed_case_once_and_sums_to_the_failed_cases():
    def case(cid, passed, failure=None):
        return {"id": cid, "kind": "question", "passed": passed, "failure_type": failure}
    cases = [case("q1", True), case("q2", False, "wrong_fact"), case("q3", False, "wrong_fact"), case("q4", False, "leak"),
             case("q5", False, "timeout"), case("q6", True)]
    out = render_panel("failures.js", {"run": {"id": "r-fixed"}, "cases": cases})
    table = out["tables"][0]
    assert [r[0] for r in table["rows"]] == FAILURE_ORDER                       # every type, in checking order
    counts = {r[0]: int(r[2].split(" of ")[0]) for r in table["rows"]}
    assert counts["wrong_fact"] == 2 and counts["leak"] == 1 and counts["timeout"] == 1
    assert sum(counts.values()) == 4 == sum(1 for c in cases if c["passed"] is False)
    assert all(r[2].endswith(" of 4") for r in table["rows"])                   # the denominator is the failed cases
    assert any("4 of 6 cases failed in run r-fixed" in n for n in out["notes"])
