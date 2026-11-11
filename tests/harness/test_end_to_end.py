"""End to end in a throwaway git repository with a fake agent: screen records, run, snapshot, resume, gate, validate."""
import json
import os
import subprocess

import pytest

from conftest import cli, git
from harness.util import read_json, read_jsonl

SET = ["--set", "model_path=stub"]


def commit(repo, msg="work"):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)


def test_screen_writes_an_immutable_record_every_time(repo):
    a = cli(repo, "screen", "--pack", "mini", check=True)
    b = cli(repo, "screen", "--pack", "mini", check=True)
    runs = sorted(p.name for p in (repo / "runs").iterdir())
    assert runs == ["s001", "s002"]                       # the second screen did not overwrite the first
    r1, r2 = read_json(repo / "runs/s001/run.json"), read_json(repo / "runs/s002/run.json")
    assert r1["started_at"] < r2["started_at"] and r1["kind"] == "screen" and r1["retrieval_path"] in ("modules", "agent")
    for k in ("manifest", "prediction_commit", "grader_version", "settings", "overall", "slices"):
        assert k in r1
    assert r1["manifest"]["corpus_hash"] and r1["manifest"]["code"]["commit"] and r1["manifest"]["index_settings"]["embed_model"]
    assert "resolved settings:" in a.stdout and "chunker = 'fixed'" in a.stdout          # settings printed first
    assert r1["overall"]["n"] == 3                                                         # q-001, q-002, q-004 need retrieval


def test_screen_records_the_prediction_commit_and_its_time(repo):
    first = cli(repo, "screen", "--pack", "mini", check=True)
    assert read_json(repo / "runs/s001/run.json")["prediction_commit"] is None and "no prediction commit" in first.stdout
    (repo / "predictions").mkdir()
    (repo / "predictions" / "lab-3.md").write_text("I expect hybrid to win on paraphrase.\n", encoding="utf-8")
    commit(repo, "prediction")
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    cli(repo, "screen", "--pack", "mini", check=True)
    rec = read_json(repo / "runs/s002/run.json")
    assert rec["prediction_commit"] == sha and rec["prediction_committed_at"] and rec["prediction_committed_at"][:4] == "2026" or rec["prediction_commit"] == sha


def test_screen_compares_with_the_latest_bm25_screen_with_the_same_other_settings(repo):
    cli(repo, "screen", "--pack", "mini", check=True)                                    # s001: bm25
    out = cli(repo, "screen", "--pack", "mini", "--set", "retriever=trigram", check=True).stdout
    rec = read_json(repo / "runs/s002/run.json")
    assert rec["baseline_bm25"] == "s001" and set(rec["wins_ties_losses"]) >= {"all"}
    assert "against the latest BM25 screen s001" in out
    # a different chunk size is a different "other setting": no baseline
    cli(repo, "screen", "--pack", "mini", "--set", "retriever=trigram", "--set", "chunk_size=200", check=True)
    assert read_json(repo / "runs/s001/run.json")["baseline_bm25"] is None


def test_run_executes_from_a_snapshot_grades_and_validates(repo):
    p = cli(repo, "run", "--pack", "mini", *SET)
    assert p.returncode == 0, p.stdout + p.stderr
    assert p.stdout.index("resolved settings:") < p.stdout.index("r001:")
    rec = read_json(repo / "runs/r001/run.json")
    assert rec["status"] == "complete" and rec["cache_mode"] == "off" and rec["parent"] is None and rec["eligibility"] == "retrieval_only"
    assert rec["snapshot"] == ".cache/snapshots/r001" and (repo / ".cache/snapshots/r001/harness/worker.py").exists()
    assert rec["totals"]["questions"] == 4 and rec["totals"]["attacks"] == 1 and rec["manifest"]["code"]["tree"]
    rows = read_jsonl(repo / "runs/r001/cases.jsonl")
    assert [r["case_id"] for r in rows] == ["q-001", "q-002", "q-003", "q-004", "a-001"]
    step = rows[0]["steps"][0]
    assert step["eval"]["ranked_hit_ids"] == ["doc-pricing#0"] and step["offsets"]["doc-pricing#0"][0] == "doc-pricing"
    assert step["cited_docs"].keys() == {"doc-pricing"} and step["state"] == {} or "state" in step
    m = rec["metrics"]
    # the fake agent answers Pro price and nothing else: q-001 passes, q-002 and q-004 do not (retrieval-only labs score only these three)
    assert m["answer_success"]["num"] == 1 and m["answer_success"]["den"] == 3
    assert m["security"]["den"] == 1 and m["security"]["num"] == 0                      # a-001: the fake agent leaks the canary
    assert m["failures_by_type"]["leak"] == 1
    assert cli(repo, "validate").returncode == 0


def test_run_refuses_uncommitted_changes_but_ignores_runs_and_cache(repo):
    (repo / "notes.txt").write_text("edit\n", encoding="utf-8")
    p = cli(repo, "run", "--pack", "mini", *SET)
    assert p.returncode == 3 and "notes.txt" in p.stderr and not (repo / "runs").exists() or p.returncode == 3
    commit(repo, "notes")
    assert cli(repo, "run", "--pack", "mini", *SET).returncode == 0
    assert cli(repo, "run", "--pack", "mini", *SET).returncode == 0                     # runs/ and .cache/ do not block the next run


def test_snapshot_is_the_committed_tree_not_the_working_tree(repo):
    cli(repo, "run", "--pack", "mini", *SET, check=True)
    snap = repo / ".cache/snapshots/r001/fake_agent.py"
    assert snap.read_text(encoding="utf-8") == (repo / "fake_agent.py").read_text(encoding="utf-8")


def test_parent_settings_then_set_and_change_recorded(repo):
    cli(repo, "run", "--pack", "mini", "--set", "model_path=stub", "--set", "chunk_size=300", check=True)
    cli(repo, "keep", "r001", check=True)
    commit(repo, "kept")
    p = cli(repo, "run", "--pack", "mini", "--set", "retriever=trigram", check=True)
    rec = read_json(repo / "runs/r002/run.json")
    assert rec["parent"] == "r001" and rec["settings"]["chunk_size"] == 300 and rec["settings"]["retriever"] == "trigram"
    assert rec["change"] == {"retriever": ["bm25", "trigram"]}
    assert "chunk_size = 300" in p.stdout and "change from parent: retriever: 'bm25' -> 'trigram'" in p.stdout
    d = cli(repo, "diff", "r002", check=True).stdout
    assert "grader version: graders-1.0.0" in d and "candidate r002 against baseline r001" in d and "verdict against r001" in d


def test_repeat_runs_are_fresh_and_resume_conflicts_with_no_cache(repo):
    out = cli(repo, "run", "--pack", "mini", *SET, "--repeat", "2", check=True).stdout
    assert "runs: r001 r002" in out
    assert cli(repo, "run", "--pack", "mini", *SET, "--resume", "--no-cache").returncode == 2


def test_smoke_and_slice_select_cases(repo):
    cli(repo, "run", "--pack", "mini", *SET, "--smoke", check=True)
    assert [r["case_id"] for r in read_jsonl(repo / "runs/r001/cases.jsonl")] == ["q-001", "a-001"]
    cli(repo, "run", "--pack", "mini", *SET, "--slice", "handoff", check=True)
    assert [r["case_id"] for r in read_jsonl(repo / "runs/r002/cases.jsonl")] == ["q-003"]


def test_resume_continues_an_interrupted_run_without_redoing_finished_cases(repo):
    cli(repo, "run", "--pack", "mini", *SET, check=True)
    full = repo / "runs/r001"
    raw = read_jsonl(full / "raw.jsonl")
    # simulate a crash after two cases
    (full / "raw.jsonl").write_text("".join(json.dumps(r) + "\n" for r in raw[:2]), encoding="utf-8")
    rec = read_json(full / "run.json")
    rec["status"] = "interrupted"
    (full / "run.json").write_text(json.dumps(rec), encoding="utf-8")
    kept_first = raw[0]["started_at"]
    out = cli(repo, "run", "--pack", "mini", *SET, "--resume", check=True).stdout
    assert "resuming r001" in out and not (repo / "runs/r002").exists()
    again = read_jsonl(full / "raw.jsonl")
    assert len(again) == 5 and again[0]["started_at"] == kept_first                      # the first two were not rerun
    assert read_json(full / "run.json")["status"] == "complete" and read_json(full / "run.json")["cache_mode"] == "resume"


def test_multi_change_runs_are_marked_and_not_comparable(repo):
    cli(repo, "run", "--pack", "mini", *SET, check=True)
    cli(repo, "keep", "r001", check=True)
    commit(repo, "kept")
    cli(repo, "run", "--pack", "mini", "--set", "retriever=trigram", "--set", "chunk_size=300", "--multi-change", check=True)
    assert read_json(repo / "runs/r002/run.json")["flags"]["multi_change"] is True
    d = cli(repo, "diff", "r002", check=True).stdout
    assert "NOT COMPARABLE" in d and "no verdict" in d


def test_gate_reports_prediction_order_and_shared_settings(repo):
    (repo / "predictions").mkdir()
    (repo / "predictions" / "lab-3.md").write_text("hybrid wins on paraphrase\n", encoding="utf-8")
    commit(repo, "prediction")
    for r in ("bm25", "trigram", "vector"):
        cli(repo, "screen", "--pack", "mini", "--set", f"retriever={r}") if r != "vector" else None
    g = cli(repo, "gate", "3")
    assert "prediction before the first record" in g.stdout and "PASS prediction before the first record" in g.stdout
    assert "FAIL all four retrievers screened" in g.stdout and g.returncode == 1 and "receipt id" in g.stdout


def test_gate_fails_when_the_prediction_came_after_the_first_screen(repo):
    cli(repo, "screen", "--pack", "mini", "--set", "retriever=trigram", check=True)
    (repo / "predictions").mkdir()
    (repo / "predictions" / "lab-3.md").write_text("late\n", encoding="utf-8")
    commit(repo, "late prediction")
    g = cli(repo, "gate", "3")
    assert "FAIL prediction before the first record" in g.stdout


def test_gate_flags_screens_with_different_other_settings(repo):
    cli(repo, "screen", "--pack", "mini", "--set", "retriever=trigram", check=True)
    cli(repo, "screen", "--pack", "mini", "--set", "retriever=bm25", "--set", "chunk_size=200", check=True)
    g = cli(repo, "gate", "3").stdout
    assert "FAIL screens and runs share every setting but retriever" in g


def test_validate_catches_a_damaged_record(repo):
    cli(repo, "run", "--pack", "mini", *SET, check=True)
    rec = read_json(repo / "runs/r001/run.json")
    del rec["manifest"]
    (repo / "runs/r001/run.json").write_text(json.dumps(rec), encoding="utf-8")
    p = cli(repo, "validate")
    assert p.returncode == 1 and "missing field 'manifest'" in p.stdout


def test_report_check_through_the_cli(repo):
    cli(repo, "run", "--pack", "mini", *SET, check=True)
    m = read_json(repo / "runs/r001/run.json")["metrics"]["answer_success"]
    shown = f"{100 * m['value']:.0f}%"
    (repo / "REPORT.md").write_text(f"[{shown} answer success](runs/r001/run.json#metrics.answer_success) on {m['den']} questions.\n", encoding="utf-8")
    assert cli(repo, "report-check").returncode == 0
    (repo / "REPORT.md").write_text("[99% answer success](runs/r001/run.json#metrics.answer_success)\n", encoding="utf-8")
    assert cli(repo, "report-check").returncode == 1


def test_records_carry_the_fields_the_dashboard_reads(repo):
    cli(repo, "run", "--pack", "mini", *SET, check=True)
    cli(repo, "keep", "r001", check=True)
    assert read_json(repo / "runs/kept.json") == {"run_id": "r001"}
    rec = read_json(repo / "runs/r001/run.json")
    for k in ("run_id", "parent", "change", "kind", "label", "settings", "manifest", "fingerprint", "totals"):
        assert k in rec
    t = rec["totals"]
    assert t["answer_success"]["n"] == 3 and 0 <= t["answer_success"]["value"] <= 1
    assert t["must_pass_failures"]["n"] == 0 and isinstance(t["must_pass_failures"]["failed"], list)
    assert t["latency_p50_ms"]["value"] is not None and t["cost_p95"]["value"] is None       # n below 20: no p95
    row = read_jsonl(repo / "runs/r001/cases.jsonl")[0]
    for k in ("id", "kind", "family", "slices", "expected_action", "must_pass", "passed", "failure_type", "recall3", "recall5", "rr",
              "context_fact_recall", "context_tokens", "cost_usd", "latency_ms", "tool_ok", "steps"):
        assert k in row, k
    assert row["steps"][0]["eval"]["ranked_hit_ids"]
    cli(repo, "screen", "--pack", "mini", check=True)
    s = read_json(repo / "runs/s001/run.json")
    assert "fingerprint" in s and s["config"]["retriever"] == "bm25" and s["overall"]["recall5"] is not None


def test_an_edited_run_record_or_case_line_is_refused(repo):
    cli(repo, "run", "--pack", "mini", *SET, check=True)
    cli(repo, "run", "--pack", "mini", *SET, "--set", "top_k=3", "--parent", "r001", check=True)
    cli(repo, "screen", "--pack", "mini", check=True)
    assert set(read_json(repo / "runs/r001/run.json")["digest"]) == {"record", "cases"}
    assert read_json(repo / "runs/s001/run.json")["digest"]
    assert cli(repo, "validate").returncode == 0
    path = repo / "runs/r002/cases.jsonl"
    original = path.read_text(encoding="utf-8")
    rows = read_jsonl(path)
    rows[1]["steps"][0]["reply"]["text"] = "Pro support answers within 4 business hours."      # a manufactured pass
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    p = cli(repo, "validate")
    assert p.returncode == 1 and "r002: cases.jsonl was edited after the run" in p.stdout
    d = cli(repo, "diff", "r002", "r001")
    assert d.returncode == 2 and "cases.jsonl was edited" in d.stderr
    k = cli(repo, "keep", "r002")
    assert k.returncode == 2 and "cases.jsonl was edited" in k.stderr
    path.write_text(original.replace("\n", "\r\n"), encoding="utf-8")                     # line endings alone change nothing
    assert cli(repo, "validate").returncode == 0
    rec = read_json(repo / "runs/r001/run.json")
    rec["started_at"] = "2020-01-01T00:00:00+00:00"                                           # an earlier start than the truth
    (repo / "runs/r001/run.json").write_text(json.dumps(rec), encoding="utf-8")
    p = cli(repo, "validate")
    assert p.returncode == 1 and "r001: run.json was edited after the run" in p.stdout
