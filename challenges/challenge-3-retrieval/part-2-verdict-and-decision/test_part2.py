"""Lab 3, part 2: the retriever panel and the lab log. Fixed fixture records only: no model, no reference numbers."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PANEL = ROOT / "dashboard" / "panels" / "recall-slices.js"


def case(cid, slices, recall5, recall3=None, rr=None):
    return {"id": cid, "kind": "question", "slices": slices, "recall5": recall5,
            "recall3": recall5 if recall3 is None else recall3, "rr": recall5 if rr is None else rr}


# Two fixture screens of the same questions. BM25: code 1 of 2, paraphrase 1 of 3. Vector: code 0 of 2, paraphrase 2 of 3.
BM25 = {"id": "s-fixture-bm25", "kind": "screen", "settings": {"retriever": "bm25"}}
BM25_CASES = [case("q1", ["code"], 1.0), case("q2", ["code"], 0.0),
              case("q3", ["paraphrase"], 0.0), case("q4", ["paraphrase"], 0.0), case("q5", ["paraphrase"], 1.0)]
VECTOR = {"id": "s-fixture-vector", "kind": "screen", "settings": {"retriever": "vector"}}
VECTOR_CASES = [case("q1", ["code"], 0.0), case("q2", ["code"], 0.0),
                case("q3", ["paraphrase"], 1.0), case("q4", ["paraphrase"], 1.0), case("q5", ["paraphrase"], 0.0)]


def draw(tmp_path, run, cases):
    """What the panel draws for one run, read from the fake DOM in panel_runner.js."""
    node = shutil.which("node")
    assert node, "install Node.js 18 or later to run the panel tests"
    data = tmp_path / "context.json"
    data.write_text(json.dumps({"run": run, "cases": cases}), encoding="utf-8")
    done = subprocess.run([node, str(HERE / "panel_runner.js"), str(PANEL), str(data)], capture_output=True, text=True, timeout=60)
    out = json.loads(done.stdout.strip().splitlines()[-1])
    assert "error" not in out, f"the panel stopped with an error: {out.get('error')}"
    return out


def row_for(drawn, slice_name):
    return next((r["cells"] for r in drawn["rows"] if r["cells"] and r["cells"][0] == slice_name and len(r["cells"]) > 2), None)


def test_retriever_panel(tmp_path):
    for run, cases, expected in ((BM25, BM25_CASES, {"code": ("2", "50%"), "paraphrase": ("3", "33%")}),
                                 (VECTOR, VECTOR_CASES, {"code": ("2", "0%"), "paraphrase": ("3", "67%")})):
        drawn = draw(tmp_path, run, cases)
        assert "Panel not built yet" not in drawn["text"], 'panel shows "Panel not built yet", expected bars'
        assert any(r["bars"] for r in drawn["rows"]), "expected a bar for each slice"
        assert "Recall at 5" in drawn["text"], "the panel must say that its bars are recall at 5"
        for name, (n, recall) in expected.items():
            row = row_for(drawn, name)
            assert row is not None, f"no row for the {name} slice in the {run['settings']['retriever']} screen"
            assert row[1] == n, f"the {name} row shows n = {row[1]}, expected {n}"
            assert recall in row, f"the {name} row for {run['settings']['retriever']} shows {row}, expected recall at 5 {recall}"


# ---- the lab log -------------------------------------------------------------------------------------------------------
LABELS = ("claim", "evidence", "cost", "next", "decision")
RUN_ID = re.compile(r"\b[rs]\d{3,}\b")

GOOD_ENTRY = """# Lab log

## Lab 3: retrieval

Claim: I kept hybrid retrieval. Its verdict against r003 was evidence of improvement.
Evidence: r007 against r003, fixed 9 and broken 2 on 120 questions. Largest win: paraphrase, 12 questions. Loss: none on code (8 questions). Screens s004 to s007.
Cost: p95 rose 0.4 seconds on a budget of 1 second. Cost per answer rose a little.
Next: try one link hop in lab 4.
Decision: keep. I ran python -m harness keep r007.
"""


def lab3_entry(text):
    marks = list(re.finditer(r"^#+\s*lab\s+(\d+)\b.*$", text, re.I | re.M))
    for i, m in enumerate(marks):
        if m.group(1) == "3":
            return text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
    return None


def check_entry(text, run_ids):
    """Return a list of what is wrong with the lab 3 entry. An empty list means the entry is complete."""
    entry = lab3_entry(text)
    if entry is None:
        return ["LAB-LOG.md has no lab 3 entry"]
    problems = []
    for label in LABELS:
        if not re.search(rf"^\W*{label}\s*:\s*\S", entry, re.I | re.M):
            problems.append(f"the lab 3 entry has no '{label.capitalize()}:' line")
    cited = set(RUN_ID.findall(entry))
    if not cited:
        problems.append("the lab 3 entry names no run id")
    for rid in sorted(cited - set(run_ids)):
        problems.append(f"the lab 3 entry names {rid}, which is not in your runs/ folder")
    decision = re.search(r"^\W*decision\s*:\s*(.*)$", entry, re.I | re.M)
    if decision and not re.search(r"\b(keep|kept|revert|reverted)\b", decision.group(1), re.I):
        problems.append("the Decision line must say keep or revert")
    return problems


def test_decision_logged():
    # The rule is checked on fixtures first, so a wrong rule shows here and not only in your log.
    assert check_entry(GOOD_ENTRY, {"r003", "r007", "s004", "s005", "s006", "s007"}) == []
    assert check_entry("# Lab log\n", set()) == ["LAB-LOG.md has no lab 3 entry"]
    assert check_entry(GOOD_ENTRY, {"r003"}), "run ids that are not in runs/ must be flagged"
    assert check_entry(GOOD_ENTRY.replace("Decision: keep", "Decision: maybe"), {"r003", "r007", "s004"}), "the decision must be keep or revert"
    assert check_entry(GOOD_ENTRY.replace("Cost:", "Money:"), {"r003", "r007"}), "the Cost line is required"
    # Then your own log. It is read from LAB-LOG.md at the repository root. A repository with no LAB-LOG.md at all
    # (the reference tree before it is exported) checks the fixture entry instead; a learner repository must have the file.
    log = ROOT / "LAB-LOG.md"
    if not log.exists():
        assert (ROOT / "facts" / "SCHEMA.md").exists(), "LAB-LOG.md has no lab 3 entry (the file is missing)"   # only the reference tree may lack a log
        text, run_ids = GOOD_ENTRY, {"r003", "r007", "s004", "s005", "s006", "s007"}
    else:
        text = log.read_text(encoding="utf-8")
        runs = ROOT / "runs"
        run_ids = {p.name for p in runs.iterdir() if p.is_dir()} if runs.exists() else set()
    problems = check_entry(text, run_ids)
    assert not problems, "; ".join(problems)


# ---- invariant: passes on the starter as well ---------------------------------------------------------------------------
@pytest.mark.invariant
def test_shell_serves_runs(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.adapters.chat import create_app

    runs = tmp_path / "runs"
    (runs / "s001").mkdir(parents=True)
    (runs / "s001" / "run.json").write_text(json.dumps({"run_id": "s001", "kind": "screen", "parent": None, "totals": {}}), encoding="utf-8")
    (runs / "s001" / "cases.jsonl").write_text(json.dumps(BM25_CASES[0]) + "\n", encoding="utf-8")
    monkeypatch.delenv("DW_TEST_MODE", raising=False)
    client = TestClient(create_app(root=ROOT, runs_dir=runs, agent_factory=lambda: object()))
    listing = client.get("/api/runs").json()
    assert [r["id"] for r in listing["runs"]] == ["s001"]
    assert client.get("/api/runs/s001").json()["cases"][0]["id"] == "q1"
    page = client.get("/dashboard")
    assert page.status_code == 200 and "recall-slices.js" in page.text
