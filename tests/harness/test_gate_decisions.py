"""Gate: which runs need a keep or revert decision, which records belong to labs 1 and 9, and prediction timing."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from conftest import ROOT  # noqa: F401  (puts the repository on sys.path)
from harness import config, gate
from harness.util import write_json

T0 = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)


def _at(minutes):
    return (T0 + timedelta(minutes=minutes)).isoformat()


def _run(rid, minutes, change=None, parent=None, from_run=None, flags=None, **over):
    return {"run_id": rid, "kind": "run", "status": "complete", "started_at": _at(minutes), "change": change or {},
            "explicit_sets": sorted(change or {}), "parent": parent, "from_run": from_run, "flags": flags or {},
            "settings": {**config.DEFAULTS, **over}, "prediction_commit": "abc", "manifest": {}}


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("DW_ROOT", str(tmp_path))
    (tmp_path / "runs").mkdir()
    for name, value in (("dirty_paths", lambda: []), ("validate_run_dir", lambda rid: []), ("git", lambda *a, **k: None),
                        ("check_results", lambda lab, part, r: None), ("prediction_files", lambda lab: [])):
        monkeypatch.setattr(gate, name, value)
    return tmp_path


def _part(root: Path, lab_dir: str, part: str, readme: str):
    d = root / "challenges" / lab_dir / part
    d.mkdir(parents=True)
    (d / "README.md").write_text(readme, encoding="utf-8")


def _gate(monkeypatch, recs, lab, part=None, kept=None):
    monkeypatch.setattr(gate, "all_runs", lambda: recs)
    monkeypatch.setattr(gate, "kept", lambda: kept or {})
    monkeypatch.setattr(gate, "load_run", lambda rid: next(r for r in recs if r["run_id"] == rid))
    r = gate.Receipt()
    gate.check(lab, part, r)
    return {n: (s, d) for s, n, d in r.rows}


def test_a_missing_decision_fails(root, monkeypatch):
    recs = [_run("r001", 0), _run("r002", 10, change={"chunker": ["fixed", "heading"]}, parent="r001", chunker="heading")]
    rows = _gate(monkeypatch, recs, 2)
    assert rows["r002 has a keep or revert decision"][0] == "FAIL"
    rows = _gate(monkeypatch, recs, 2, kept={"decisions": [{"run": "r002", "action": "revert"}]})
    assert rows["r002 has a keep or revert decision"][0] == "PASS"


def test_the_last_run_may_wait_for_a_later_part_that_asks_for_the_decision(root, monkeypatch):
    _part(root, "challenge-2-x", "part-1-run", "Start the candidate's full run.\n")
    _part(root, "challenge-2-x", "part-2-decide", "Run `python -m harness keep <run>` or `python -m harness revert <run>`.\n")
    recs = [_run("r001", 0), _run("r002", 10, change={"chunk_size": [400, 300]}, parent="r001", chunk_size=300),
            _run("r003", 20, change={"chunker": ["fixed", "heading"]}, parent="r001", chunker="heading")]
    rows = _gate(monkeypatch, recs, 2, part=1)
    assert rows["r003 has a keep or revert decision"][0] == "WARN" and "part 2" in rows["r003 has a keep or revert decision"][1]
    assert rows["r002 has a keep or revert decision"][0] == "FAIL"                 # only the lab's last run may wait
    rows = _gate(monkeypatch, recs, 2, part=2)
    assert rows["r003 has a keep or revert decision"][0] == "FAIL"
    rows = _gate(monkeypatch, recs, 2)
    assert rows["r003 has a keep or revert decision"][0] == "FAIL"


def test_the_model_switch_decided_in_the_capstone_may_wait(root, monkeypatch):
    _part(root, "challenge-8-x", "part-2-path", "Start a full run on the other path.\n")
    _part(root, "challenge-9-x", "part-1-confirm", "Set up. If you started a full run for a model switch in 8.5, read it "
          "and keep it (`python -m harness keep <run>`) or turn it down.\n")
    recs = [_run("r001", 0), _run("r002", 10, change={"model_path": ["local", "hosted"]}, parent="r001", model_path="hosted",
                                  hosted_model="h")]
    rows = _gate(monkeypatch, recs, 8)
    assert rows["r002 has a keep or revert decision"][0] == "WARN"
    assert gate.decision_comes_later(7, None) is None


def test_smoke_and_slice_runs_are_not_candidates(root, monkeypatch):
    recs = [_run("r001", 0),
            _run("r002", 10, change={"tools": ["off", "on"]}, parent="r001", flags={"slice": "tool"}, tools="on"),
            _run("r003", 20, change={"tools": ["off", "on"]}, parent="r001", flags={"smoke": True}, tools="on")]
    rows = _gate(monkeypatch, recs, 5)
    assert rows["a complete full run for lab 5"][0] == "FAIL"
    assert not any(n.startswith(("r002", "r003")) for n in rows)


def test_lab1_noise_reruns_count_after_an_early_keep(root, monkeypatch):
    recs = [_run("r001", 0), _run("r002", 10, parent="r001"), _run("r003", 20, parent="r001"),
            _run("r004", 30, change={"top_k": [5, 3]}, parent="r001", top_k=3),
            _run("r005", 40, parent="r004", top_k=3)]                                   # a rerun of a changed setup
    monkeypatch.setattr(gate, "all_runs", lambda: recs)
    assert [r["run_id"] for r in gate.lab_records(1)] == ["r001", "r002", "r003", "r004"]
    rows = _gate(monkeypatch, recs, 1)
    assert rows["noise floor: three runs of the same settings"] == ("PASS", "3 found")
    assert "r002 has a keep or revert decision" not in rows                           # noise reruns are not candidates
    assert rows["r004 has a keep or revert decision"][0] == "FAIL"


def test_lab9_owns_the_confirmation_runs(root, monkeypatch):
    best = [_run(f"r01{i}", 10 + i, from_run="r005", chunker="heading") for i in range(3)]
    base = [_run(f"r02{i}", 20 + i, from_run="r001") for i in range(3)]
    other = _run("r030", 30, change={"chunker": ["fixed", "heading"]}, parent="r001", chunker="heading")
    write_json(root / "runs" / "confirm-r010.json", {"best": {"runs": ["r010", "r011", "r012"]},
                                                     "baseline": {"runs": ["r020", "r021", "r022"]}})
    monkeypatch.setattr(gate, "all_runs", lambda: best + base + [other])
    assert [r["run_id"] for r in gate.lab_records(9)] == ["r010", "r011", "r012", "r020", "r021", "r022"]
    rows = _gate(monkeypatch, best + base + [other], 9)
    assert rows["confirmation artifact"][0] == "PASS"
    assert not any("decision" in n or "share every setting" in n for n in rows)


def test_the_gate_matches_each_run_with_the_prediction_committed_before_it(root, monkeypatch):
    files = [root / "predictions" / "lab4-authority.md", root / "predictions" / "lab4-context.md"]
    times = {files[1]: _at(-10), files[0]: _at(25)}                     # authority written after part 1's runs
    recs = [_run("r001", 0, change={"context": ["none", "neighbours"]}, context="neighbours"),
            _run("r002", 10, change={"neighbours_n": [1, 2]}, context="neighbours", neighbours_n=2),   # names no file
            _run("r003", 30, change={"authority_rule": ["off", "on"]}, context="neighbours", authority_rule="on")]
    monkeypatch.setattr(gate, "prediction_files", lambda lab: files)
    monkeypatch.setattr(gate, "first_commit_time", lambda f: times[f])
    monkeypatch.setattr(gate, "prediction_text_at", lambda f, when: ("a prediction", []))
    rows = [(s, n, d) for s, n, d in _rows_of(monkeypatch, recs, 4)]
    preds = [(s, d.split(" ")[0]) for s, n, d in rows if n == "prediction before the first record"]
    assert preds == [("PASS", "lab4-context.md"), ("PASS", "lab4-authority.md")]


def test_an_empty_prediction_or_one_edited_after_the_record(root, monkeypatch):
    f = root / "predictions" / "lab3.md"
    monkeypatch.setattr(gate, "prediction_files", lambda lab: [f])
    monkeypatch.setattr(gate, "first_commit_time", lambda p: _at(-5))
    recs = [_run("r001", 0, change={"retriever": ["bm25", "hybrid"]}, retriever="hybrid")]
    monkeypatch.setattr(gate, "prediction_text_at", lambda p, when: ("", ["c2"]))
    rows = _rows_of(monkeypatch, recs, 3)
    assert ("FAIL", "prediction before the first record") in [(s, n) for s, n, _ in rows]
    monkeypatch.setattr(gate, "prediction_text_at", lambda p, when: ("hybrid wins", ["c2"]))
    rows = _rows_of(monkeypatch, recs, 3)
    assert ("PASS", "prediction before the first record") in [(s, n) for s, n, _ in rows]
    assert ("WARN", "prediction unchanged after the first record") in [(s, n) for s, n, _ in rows]


def _rows_of(monkeypatch, recs, lab):
    monkeypatch.setattr(gate, "all_runs", lambda: recs)
    monkeypatch.setattr(gate, "kept", lambda: {"decisions": [{"run": r["run_id"], "action": "keep"} for r in recs]})
    r = gate.Receipt()
    gate.check(lab, None, r)
    return r.rows
