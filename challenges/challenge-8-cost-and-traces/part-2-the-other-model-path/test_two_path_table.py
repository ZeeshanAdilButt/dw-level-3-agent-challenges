"""Lab 8, part 2: the two-path table. The panel is drawn on two fixed run records; the pairing rule is checked on fixed
settings; no real run is read and no reference number is used.

On the starter the panel draws "Panel not built yet" and the first test fails with: AssertionError: no two-path rows
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
for p in (ROOT, ROOT / "challenges" / "challenge-8-cost-and-traces"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from panel_helper import needs_node, render_panel  # noqa: E402

from app.model import cost  # noqa: E402
from app.settings import DEFAULTS  # noqa: E402
from harness.diff import comparable  # noqa: E402


def run(run_id, path, answer, security, cost50, cost95, lat50, lat95, model="qwen3:4b-instruct", hosted_model=""):
    return {"id": run_id, "kind": "run", "settings": {**DEFAULTS, "model_path": path, "model": model, "hosted_model": hosted_model},
            "totals": {"answer_success": {"value": answer, "n": 30}, "security_pass_rate": {"value": security, "n": 10},
                       "cost_p50": {"value": cost50, "n": 40}, "cost_p95": {"value": cost95, "n": 40},
                       "latency_p50_ms": {"value": lat50, "n": 40}, "latency_p95_ms": {"value": lat95, "n": 40}}}


LOCAL = run("r-local", "local", 0.8, 0.9, 0.0, 0.0, 3000, 9000)
HOSTED = run("r-hosted", "hosted", 0.7, 0.8, 0.0002, 0.0006, 1000, 2500, hosted_model="claude-haiku-5-5")


@needs_node
def test_the_table_has_one_row_per_path_with_quality_cost_and_time_in_separate_columns():
    out = render_panel("two-path.js", {"runs": [LOCAL, HOSTED], "run": None, "cases": []})
    assert out["tables"], "no two-path rows"
    table = out["tables"][0]
    assert table["head"][:3] == ["Path", "Run", "Model"]
    assert [r[0] for r in table["rows"]] == ["local", "hosted"]
    local, hosted = table["rows"]
    head = table["head"]
    cell = lambda row, name: row[head.index(name)]  # noqa: E731
    assert cell(local, "Answer success") == "80% of 30" and cell(hosted, "Answer success") == "70% of 30"
    assert cell(local, "Attacks passed") == "90% of 10" and cell(hosted, "Attacks passed") == "80% of 10"      # not mixed with answer success
    assert cell(local, "Cost p50") == "$0" and cell(hosted, "Cost p50") == "$0.00020"
    assert cell(hosted, "Cost p95") == "$0.00060"
    assert cell(local, "Latency p50") == "3.0 s" and cell(local, "Latency p95") == "9.0 s"
    assert cell(hosted, "Latency p95") == "2.5 s"


@needs_node
def test_a_path_with_no_run_says_so_instead_of_showing_zero():
    out = render_panel("two-path.js", {"runs": [LOCAL], "run": None, "cases": []})
    hosted = out["tables"][0]["rows"][1]
    assert hosted[0] == "hosted" and hosted[1] == "no run on this path yet"
    assert "0%" not in "".join(hosted[2:])


@needs_node
def test_the_note_says_a_switch_is_decided_on_a_full_run():
    out = render_panel("two-path.js", {"runs": [LOCAL, HOSTED], "run": None, "cases": []})
    assert any("full run" in n for n in out["notes"])


def test_two_smoke_runs_that_differ_only_in_model_path_are_comparable():
    ok, why, diffs = comparable({**LOCAL, "manifest": {"question_set_version": "v1"}, "pack": "juniper"},
                                {**HOSTED, "manifest": {"question_set_version": "v1"}, "pack": "juniper"})
    assert diffs == ["model_path", "hosted_model"] and ok, why                    # the model group is one change


def test_a_second_change_makes_the_pair_not_comparable():
    other = {**HOSTED, "settings": {**HOSTED["settings"], "retriever": "hybrid"}, "manifest": {"question_set_version": "v1"}, "pack": "juniper"}
    ok, why, _ = comparable({**LOCAL, "manifest": {"question_set_version": "v1"}, "pack": "juniper"}, other)
    assert not ok and "the model and other settings differ" in why[0]


def test_a_local_run_has_a_hosted_equivalent_price():
    paid, equivalent = cost("qwen3:4b-instruct", 2000, 400)
    assert paid == 0.0
    assert equivalent == pytest.approx((2000 * 0.10 + 400 * 0.50) / 1e6)           # from config/prices.toml
    assert cost("claude-haiku-5-5", 2000, 400)[0] == pytest.approx(equivalent)       # the hosted model costs the same tokens the same
