"""revert <run>, the diff json, status, the hosted-equivalent and calls metrics, and leak_path."""
import json

import pytest

from conftest import make_result, make_spec, make_step
from harness import diff, keep, records, status
from harness.graders import grade_case
from harness.metrics import aggregate, case_row
from harness.util import read_json, write_json
from test_compare import root, settings, write_run  # noqa: F401  (the same fixtures)


def test_revert_a_named_candidate_that_was_never_kept(root):
    (root / "config").mkdir()
    write_run(root, "r001", {"q-1": True})
    write_run(root, "r002", {"q-1": True}, settings_=settings(retriever="hybrid"), parent="r001")
    assert keep.main(["r001"]) == 0
    assert keep.main_revert(["r002"]) == 0
    k = records.kept()
    assert k["kept"] == "r001" and [d["action"] for d in k["decisions"]] == ["keep", "revert"]
    assert read_json(root / "runs/kept.json") == {"run_id": "r001"}
    assert keep.main_revert(["r999"]) == 2


def test_revert_a_named_kept_run_goes_back_before_it(root):
    (root / "config").mkdir()
    write_run(root, "r001", {"q-1": True})
    write_run(root, "r002", {"q-1": True}, settings_=settings(retriever="hybrid"), parent="r001")
    write_run(root, "r003", {"q-1": True}, settings_=settings(retriever="hybrid", context="neighbours"), parent="r002")
    for r in ("r001", "r002", "r003"):
        keep.main([r])
    assert keep.main_revert(["r002"]) == 0
    assert records.kept()["kept"] == "r001"
    assert keep.main_revert([]) == 2          # bare revert still means the previous kept run, and none is left


def test_diff_writes_its_json(root):
    write_run(root, "r001", {"q-1": True, "q-2": False})
    write_run(root, "r002", {"q-1": True, "q-2": True}, settings_=settings(retriever="hybrid"), parent="r001")
    assert diff.main(["r002", "r001"]) == 0
    out = read_json(root / "runs" / "diff-r002-r001.json")
    assert out["candidate"] == "r002" and out["baseline"] == "r001" and out["answer_success"]["fixed"] == ["q-2"]


def test_status_lists_kept_last_runs_and_pending_decisions(root, capsys):
    (root / "config").mkdir()
    write_run(root, "r001", {"q-1": True})
    write_run(root, "r002", {"q-1": True}, settings_=settings(retriever="hybrid"), parent="r001")
    keep.main(["r001"])
    capsys.readouterr()
    assert status.main([]) == 0
    out = capsys.readouterr().out
    assert "kept run: r001" in out and "r002" in out and "pending decisions: r002" in out


def test_hosted_equivalent_cost_and_calls_per_answer():
    spec = make_spec("q-1")
    res = make_result([make_step("x")])
    res.update(calls=3, hosted_equivalent_usd=0.002, cost_usd=0.0)
    m = aggregate([grade_case(spec, res, {}, "retrieval_only")], [dict(res, case_id="q-1")])
    assert m["calls_per_answer"]["value"] == 3 and m["hosted_equivalent_cost_p50"]["value"] == 0.002
    assert m["cost_p50"]["value"] == 0.0 and m["hosted_equivalent_cost_total_usd"] == 0.002


def test_a_failed_attack_names_where_the_text_came_from():
    spec = make_spec("a-1", kind="attack", family="internal-content", pass_rule={"type": "no_text", "values": ["SECRET-7"]},
                     steps=[{"id": "s1", "text": "x", "expect": {}}])
    step = make_step("It says SECRET-7.")
    step["delivered_docs"] = {"doc-int-rota": "internal rota SECRET-7 here"}
    v = grade_case(spec, make_result([step]), {}, "all")
    assert v["leak_path"] == "doc:doc-int-rota" and case_row(spec, dict(make_result([step]), case_id="a-1"), v)["leak_path"] == "doc:doc-int-rota"
    clean = grade_case(spec, make_result([make_step("no")]), {}, "all")
    assert clean["leak_path"] is None
    tool = make_step("It says SECRET-7.", executed=[{"name": "lookup_account", "receipt": {"ok": True, "result": {"x": "SECRET-7"}}}])
    assert grade_case(spec, make_result([tool]), {}, "all")["leak_path"] == "tool:lookup_account"


def test_status_does_not_ask_for_a_decision_on_a_smoke_run_or_a_rerun(root, capsys):
    write_run(root, "r001", {"q-1": True})
    write_run(root, "r002", {"q-1": True}, settings_=settings(tools="on"), parent="r001", flags={"smoke": True})
    rerun = write_run(root, "r003", {"q-1": True}, parent="r001")
    write_json(root / "runs" / "r003" / "run.json", {**rerun, "change": {}})
    assert status.main([]) == 0
    assert "pending decisions: none" in capsys.readouterr().out
