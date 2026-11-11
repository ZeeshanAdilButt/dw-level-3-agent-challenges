"""Lab 2, part 2: the verdict and the decision. The panel runs in Node on fixed run records: no browser, no reference numbers.

Invariant (passes on the starter): test_shell_serves_runs, test_the_decision_rule_on_fixed_cases.
Acceptance (fails on the starter): test_slice_panel (AssertionError: panel shows "Panel not built yet", expected bars)
and test_decision_logged (AssertionError: LAB-LOG.md has no lab 2 entry).
"""
import json
import re
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "challenges" / "_shared"))

from panel_render import is_reference_tree, render_panel  # noqa: E402


def case(cid, slice_name, facts):
    return {"id": cid, "kind": "question", "expected_action": "answer", "slices": [slice_name], "context_fact_recall": facts,
            "recall3": 1.0, "recall5": 1.0, "rr": 0.5}


def run_cases(table, far):
    return ([case(f"q-t{i}", "table", v) for i, v in enumerate(table)]
            + [case(f"q-h{i}", "far-from-heading", v) for i, v in enumerate(far)])


def pcts(row):
    return [float(m) for cell in row for m in re.findall(r"(\d+(?:\.\d+)?)%", cell)]


def slice_rows(out, name):
    """Every row, in every table, that starts with the slice name (a panel may draw the slice in more than one table)."""
    return [row for table in out["tables"] for row in table if row and row[0] == name]


# ---- acceptance: the slice panel -----------------------------------------------------------------------------------

def test_slice_panel():
    runs = [{"id": "r001", "parent": None, "kind": "run", "change": None, "settings": {}},
            {"id": "r002", "parent": "r001", "kind": "run", "change": {"chunker": ["fixed", "heading"]}, "settings": {}}]
    base_cases = run_cases([0.0, 0.5, 0.0, 0.5], [1.0, 0.0, 0.0])        # table 25 percent over 4, far 33 percent over 3
    cand_cases = run_cases([1.0, 0.5, 0.0, 0.5], [1.0, 1.0, 0.0])        # table 50 percent over 4, far 67 percent over 3
    for run, cases, want_table, want_far in ((runs[1], cand_cases, 50, 66.7), (runs[0], base_cases, 25, 33.3)):
        out = render_panel("recall-slices.js", {"run": run, "base": None, "runs": runs, "kept": "r001", "cases": cases, "baseCases": []})
        assert not out["notBuilt"], 'panel shows "Panel not built yet", expected bars'
        assert out["tables"], "expected bars: the panel drew no table"
        t, f = slice_rows(out, "table"), slice_rows(out, "far-from-heading")
        assert t and f, "a row for each of the slices table and far-from-heading is needed"
        assert all("4" in row for row in t) and all("3" in row for row in f), "every slice shows its n"
        assert any(abs(p - want_table) < 0.6 for row in t for p in pcts(row)), f"table slice should show about {want_table} percent, drew {t}"
        assert any(abs(p - want_far) < 0.6 for row in f for p in pcts(row)), f"far-from-heading slice should show about {want_far} percent, drew {f}"
    # a run with no sliced cases says so, and does not draw 0 percent
    out = render_panel("recall-slices.js", {"run": runs[0], "base": None, "runs": runs, "kept": "r001", "cases": [], "baseCases": []})
    assert not out["notBuilt"] and "0%" not in out["text"].replace("n/a", "")


# ---- the decision rule, printed once in 2.4 ------------------------------------------------------------------------

def expected_decision(verdict: str, token_change_pct: float, argued: bool = False, cheaper_or_simpler: bool = False,
                      budget_pct: float = 25.0) -> str:
    """Keep a change only if the full run shows evidence of improvement and its extra cost stays inside the budget (or the log
    argues for going over it). With no evidence either way, keep only a change that makes the agent cheaper or simpler. Else revert."""
    if verdict.startswith("evidence of improvement"):
        return "keep" if token_change_pct <= budget_pct or argued else "revert"
    if verdict.startswith("inconclusive"):
        return "keep" if cheaper_or_simpler else "revert"
    return "revert"                                                    # evidence of harm


def test_the_decision_rule_on_fixed_cases():
    assert expected_decision("evidence of improvement", 31.0) == "revert"                  # the 2.5 predict: over budget, not argued
    assert expected_decision("evidence of improvement", 31.0, argued=True) == "keep"
    assert expected_decision("evidence of improvement", 24.9) == "keep"
    assert expected_decision("inconclusive", 0.0) == "revert"
    assert expected_decision("inconclusive", -5.0, cheaper_or_simpler=True) == "keep"
    assert expected_decision("evidence of harm", -10.0, cheaper_or_simpler=True) == "revert"


# ---- acceptance: the lab 2 entry in LAB-LOG.md ---------------------------------------------------------------------

def log_problems(log: str, run_ids: set, decided: dict) -> list:
    """Problems with the lab 2 entry. decided maps a run id to 'keep' or 'revert', read from runs/kept-history.json."""
    m = re.search(r"^#{1,3}\s*Lab 2\b.*?(?=^#{1,3}\s*Lab \d|\Z)", log, re.M | re.S | re.I)
    if not m:
        return ["LAB-LOG.md has no lab 2 entry"]
    entry, problems = m.group(0), []
    for label in ("claim", "evidence", "cost", "next"):
        if not re.search(rf"^\W*{label}\b\s*[:\-]", entry, re.M | re.I):
            problems.append(f"the entry has no '{label}' line")
    ev = re.search(r"^\W*evidence\b.*$", entry, re.M | re.I)
    ids = list(dict.fromkeys(re.findall(r"\b[rs]\d{3,}\b", ev.group(0)))) if ev else []   # in order: the candidate comes first
    if len(ids) < 2:
        problems.append("the evidence line names fewer than two run ids")
    unknown = sorted(set(ids) - run_ids)
    if unknown:
        problems.append("the evidence line names runs that are not in your runs/ folder: " + ", ".join(unknown))
    d = re.search(r"^\W*decision\b\s*[:\-]\s*(keep|revert)", entry, re.M | re.I)
    if not d:
        problems.append("the entry has no 'decision: keep' or 'decision: revert' line")
    else:
        word = d.group(1).lower()
        candidate = ids[0] if ids else None                           # the evidence line names the candidate first, then its parent
        if candidate not in decided:
            problems.append(f"the first run on the evidence line ({candidate}) has no recorded keep or revert decision (run harness keep or harness revert)")
        elif decided[candidate] != word:
            problems.append(f"the log says {word} but harness recorded {decided[candidate]} for {candidate}")
    return problems


GOOD_LOG = """# Lab log

## Lab 1

Claim: baseline measured.

## Lab 2: chunking

Claim: heading chunks reverted.
Evidence: r005 against r003, 2 fixed and 7 broken, p 0.180, inconclusive.
Cost: context tokens up 12 percent against the 25 percent budget.
Next: try a different retriever in lab 3.
Decision: revert
"""


def test_the_log_checker_on_fixed_logs():
    ids = {"r003", "r005"}
    assert log_problems(GOOD_LOG, ids, {"r005": "revert"}) == []
    assert log_problems(GOOD_LOG, ids, {"r003": "keep", "r005": "revert"}) == []           # the parent was kept in lab 1: only the candidate counts
    assert log_problems(GOOD_LOG.replace("Decision: revert", "Decision: keep"), ids, {"r003": "keep"})    # keep logged but the candidate was never kept
    assert log_problems(GOOD_LOG, ids, {"r005": "keep"})                                   # log and harness disagree
    assert log_problems(GOOD_LOG.replace("r005", "r009"), ids, {"r005": "revert"})         # a run that does not exist
    assert log_problems(GOOD_LOG.replace("Cost:", "Money:"), ids, {"r005": "revert"})      # no cost line
    assert log_problems("# Lab log\n\nOne entry per lab.\n", ids, {}) == ["LAB-LOG.md has no lab 2 entry"]


@pytest.mark.skipif(is_reference_tree(), reason="the reference tree holds no learner log; the checker is tested above")
def test_decision_logged():
    from harness.records import all_runs, kept
    log_file = ROOT / "LAB-LOG.md"
    log = log_file.read_text(encoding="utf-8") if log_file.exists() else ""
    decided = {d["run"]: d["action"] for d in kept().get("decisions") or []}
    problems = log_problems(log, {r["run_id"] for r in all_runs()}, decided)
    assert not problems, "; ".join(problems)


# ---- invariant ---------------------------------------------------------------------------------------------------

def test_shell_serves_runs():
    from fastapi.testclient import TestClient
    from app.adapters.chat import create_app
    with tempfile.TemporaryDirectory() as tmp:
        runs = Path(tmp) / "runs"
        (runs / "r-001").mkdir(parents=True)
        (runs / "r-001" / "run.json").write_text(json.dumps({"run_id": "r-001", "parent": None, "change": None, "totals": {}}), encoding="utf-8")
        (runs / "r-001" / "cases.jsonl").write_text(json.dumps(case("q-001", "table", 1.0)) + "\n", encoding="utf-8")
        client = TestClient(create_app(root=ROOT, runs_dir=runs, agent_factory=lambda: object()))
        listing = client.get("/api/runs").json()
        one = client.get("/api/runs/r-001").json()
    assert [r["id"] for r in listing["runs"]] == ["r-001"]
    assert one["cases"][0]["slices"] == ["table"]
