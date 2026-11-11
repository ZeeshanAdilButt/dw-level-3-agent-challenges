"""Lab 1, part 4: the dashboard and the first verdict. Panels run in Node on fixed run records (no browser, no reference numbers).

Invariant (passes on the starter): test_headline, test_shell_serves_runs.
Acceptance (fails on the starter): test_diff_verdict and test_run_tree, with
    AssertionError: panel shows "Panel not built yet", expected a table
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "challenges" / "_shared"))

from panel_render import render_panel  # noqa: E402


def question(cid, passed):
    return {"id": cid, "kind": "question", "expected_action": "answer", "passed": passed, "slices": ["table"]}


def runs_fixture():
    return [
        {"id": "r001", "parent": None, "kind": "run", "change": None, "settings": {"model_path": "stub"}, "totals": {}},
        {"id": "r002", "parent": "r001", "kind": "run", "change": {"chunk_size": [400, 800]},
         "settings": {"model_path": "stub"}, "totals": {}},
        {"id": "r003", "parent": "r002", "kind": "run", "change": {"retriever": ["bm25", "hybrid"]},
         "settings": {"model_path": "stub"}, "totals": {}},
        {"id": "r004", "parent": None, "kind": "run", "change": None, "settings": {"model_path": "stub"}, "totals": {}},
    ]


def pair(fixed, broken, same_pass=2, same_fail=1):
    """Cases of a run and of its baseline with exactly `fixed` fixed and `broken` broken questions."""
    base, now = [], []
    for i in range(fixed):
        base.append(question(f"q-f{i}", False)), now.append(question(f"q-f{i}", True))
    for i in range(broken):
        base.append(question(f"q-b{i}", True)), now.append(question(f"q-b{i}", False))
    for i in range(same_pass):
        base.append(question(f"q-p{i}", True)), now.append(question(f"q-p{i}", True))
    for i in range(same_fail):
        base.append(question(f"q-x{i}", False)), now.append(question(f"q-x{i}", False))
    return now, base


def drawn(panel, ctx):
    out = render_panel(panel, ctx)
    assert not out["notBuilt"], 'panel shows "Panel not built yet", expected a table'
    assert out["tables"], 'panel drew no table: expected a table'
    return out


def cell(out, label_part, col=1):
    """The cell of the first row, in any table, whose first cell holds label_part."""
    for table in out["tables"]:
        for row in table:
            if row and label_part.lower() in row[0].lower() and len(row) > col:
                return row[col]
    return None


def diff_ctx(fixed, broken):
    runs = runs_fixture()
    now, base = pair(fixed, broken)
    return {"run": runs[1], "base": runs[0], "runs": runs, "kept": "r001", "cases": now, "baseCases": base}


# ---- acceptance --------------------------------------------------------------------------------------------------

def test_diff_verdict():
    out = drawn("diff.js", diff_ctx(fixed=10, broken=1))          # sign test on 11 flips: p is about 0.012
    assert cell(out, "fixed") == "10" and cell(out, "broken") == "1"
    assert "evidence of improvement" in out["text"]
    assert cell(out, "sign test").startswith("0.01")
    flipped = {row[0] for table in out["tables"] for row in table if row and row[0].startswith("q-")}
    assert "q-f0" in flipped and "q-b0" in flipped and "q-p0" not in flipped      # only the flipped cases are listed

    out = drawn("diff.js", diff_ctx(fixed=4, broken=3))           # p is 1.000: nothing can be claimed
    assert "inconclusive" in out["text"] and "evidence" not in out["text"].replace("Verdicts here use", "")

    out = drawn("diff.js", diff_ctx(fixed=1, broken=9))
    assert "evidence of harm" in out["text"]

    ctx = diff_ctx(fixed=0, broken=0)
    out = drawn("diff.js", ctx)                                   # nothing changed: say so, do not print a p
    assert cell(out, "fixed") == "0" and cell(out, "broken") == "0" and "inconclusive" in out["text"]


def test_run_tree():
    ctx = diff_ctx(1, 0)
    out = drawn("run-tree.js", ctx)
    order = [row[0] for row in out["tables"][0][1:]]
    ids = [next(i for i in ("r001", "r002", "r003", "r004") if i in label) for label in order]
    assert ids == ["r001", "r002", "r003", "r004"]                # a child sits straight under its parent
    assert "(kept)" in order[0]
    # a child is drawn apart from its parent: the label differs from a root's only by the marker or the indent
    assert order[1] != "r002" or "padding" in json.dumps(out)


# ---- invariant ---------------------------------------------------------------------------------------------------

def test_headline():
    runs = runs_fixture()
    runs[1]["totals"] = {"answer_success": {"value": 0.5, "n": 20}, "recall5": {"value": 0.75, "n": 16}}
    runs[0]["totals"] = {"answer_success": {"value": 0.4, "n": 20}}
    out = render_panel("headline.js", {"run": runs[1], "base": runs[0], "runs": runs, "kept": "r001", "cases": [], "baseCases": []})
    rows = {r[0]: r for r in out["tables"][0]}
    assert rows["Answer success"][1] == "50.0%" and rows["Answer success"][2] == "20"
    assert rows["Recall at 5"][1] == "75.0%" and rows["Recall at 5"][2] == "16"
    assert "n/a" not in rows["Answer success"][1]


def test_shell_serves_runs():
    from fastapi.testclient import TestClient
    from app.adapters.chat import create_app
    with tempfile.TemporaryDirectory() as tmp:
        runs = Path(tmp) / "runs"
        (runs / "r-001").mkdir(parents=True)
        (runs / "r-001" / "run.json").write_text(json.dumps({"run_id": "r-001", "parent": None, "change": None, "totals": {}}), encoding="utf-8")
        (runs / "r-001" / "cases.jsonl").write_text(json.dumps(question("q-001", True)) + "\n", encoding="utf-8")
        client = TestClient(create_app(root=ROOT, runs_dir=runs, agent_factory=lambda: object()))
        listing = client.get("/api/runs").json()
        one = client.get("/api/runs/r-001").json()
        page = client.get("/dashboard")
    assert [r["id"] for r in listing["runs"]] == ["r-001"]
    assert len(one["cases"]) == 1
    assert page.status_code == 200
