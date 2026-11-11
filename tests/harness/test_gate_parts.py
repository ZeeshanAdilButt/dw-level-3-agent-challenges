"""Gate unit tests: which parts must hold results.md, which prediction file a run belongs to, and `gate capstone`."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from conftest import ROOT  # noqa: F401  (puts the repository on sys.path)
from harness import gate, paths


def _part(root: Path, lab_dir: str, part: str, readme: str, results=None):
    d = root / "challenges" / lab_dir / part
    d.mkdir(parents=True)
    (d / "README.md").write_text(readme, encoding="utf-8")
    if results is not None:
        (d / "results.md").write_text(results, encoding="utf-8")
    return d


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("DW_ROOT", str(tmp_path))
    monkeypatch.setattr(gate, "all_runs", lambda: [{"run_id": "r001"}])
    return tmp_path


def _rows(lab=1, part=None):
    r = gate.Receipt()
    gate.check_results(lab, part, r)
    return r.rows


def test_a_part_that_never_asks_for_results_needs_none(root):
    _part(root, "challenge-1-x", "part-2-cited", "Build the agent. Run the tests.\n")
    assert [s for s, _, _ in _rows()] == []


def test_a_part_that_asks_for_results_fails_without_it(root):
    _part(root, "challenge-1-x", "part-1-setup", "Write `results.md` in this folder: paste the doctor output.\n")
    rows = _rows()
    assert [(s, n.endswith("results.md")) for s, n, _ in rows] == [("FAIL", True)]


@pytest.mark.parametrize("sentence", [
    "Save the per-family table, with the run ids, in this part's `results.md`.",
    "Save it in `LAB-LOG.md` and in this part's `results.md`.",
    "Write a smoke table (case, verdict, reason) in `results.md`.",
])
def test_the_asking_sentences_are_detected(root, sentence):
    d = _part(root, "challenge-1-x", "part-1-a", sentence + "\n")
    assert gate.asks_for_results(d)


@pytest.mark.parametrize("sentence", [
    "The gate checks that `results.md` cites only your own runs.",
    "Commit `results.md`, `config/settings.toml` and `.gitignore`. Write the code first.",
])
def test_a_passing_mention_is_not_a_request(root, sentence):
    d = _part(root, "challenge-1-x", "part-1-a", sentence + "\n")
    assert not gate.asks_for_results(d)


def test_an_existing_results_file_is_still_checked_for_unknown_runs(root):
    _part(root, "challenge-1-x", "part-2-b", "Nothing to write.\n", results="r001 and r999\n")
    rows = _rows()
    assert [s for s, _, _ in rows] == ["FAIL"] and "r999" in rows[0][2]


def test_every_real_part_that_asks_for_results_is_known():
    """Guards the README wording the detector relies on: these parts ask, the rest do not."""
    ask = {(d.parent.name.split("-")[1], d.name) for lab in range(1, 10) for d in _all_parts(lab) if gate.asks_for_results(d)}
    assert ("1", "part-1-setup-and-doctor") in ask and ("1", "part-2-cited-agent") not in ask
    assert ("3", "part-2-verdict-and-decision") not in ask and ("7", "part-2-two-more-defences") in ask


def _all_parts(lab):
    base = ROOT / "challenges"
    for c in sorted(base.glob(f"challenge-{lab}-*")):
        yield from sorted(p for p in c.glob("part-*") if p.is_dir())


# ---- prediction files ---------------------------------------------------------------------------------------------

T0 = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)


def _at(minutes):
    return (T0 + timedelta(minutes=minutes)).isoformat()


def _rec(run_id, minutes, change=None, sets=None, **settings):
    return {"run_id": run_id, "kind": "run", "started_at": _at(minutes), "change": change or {},
            "explicit_sets": sets or [], "settings": settings, "prediction_commit": "abc"}


def _files(*names):
    return [Path("predictions") / n for n in names]


def test_lab4_part2_prediction_written_after_part1_runs_passes(monkeypatch):
    files = _files("lab4-authority.md", "lab4-context.md")
    times = {files[1]: _at(0), files[0]: _at(60)}      # context first, authority after part 1's runs
    part1 = [_rec("s001", 10, sets=["context"]), _rec("r001", 20, change={"context": ["none", "neighbours"]}),
             _rec("r002", 30, change={"neighbours_n": [1, 2]})]
    part2 = [_rec("s002", 70, sets=["authority_rule"]), _rec("r003", 80, change={"authority_rule": ["off", "on"]})]
    own = {}
    for rec in part1 + part2:
        own.setdefault(gate.prediction_for(rec, files, times), rec)
    assert {f.name: r["run_id"] for f, r in own.items()} == {"lab4-context.md": "s001", "lab4-authority.md": "s002"}


def test_a_run_naming_no_file_uses_the_latest_prediction_already_committed():
    files = _files("lab5-rules.md", "lab5-tools.md")
    times = {files[1]: _at(0), files[0]: _at(60)}
    assert gate.prediction_for(_rec("r1", 10, change={"top_k": [5, 6]}), files, times).name == "lab5-tools.md"
    assert gate.prediction_for(_rec("r2", 90, change={"top_k": [5, 6]}), files, times).name == "lab5-rules.md"
    assert gate.prediction_for(_rec("r3", -5, change={"top_k": [5, 6]}), files, times).name == "lab5-tools.md"   # none yet: earliest


@pytest.mark.parametrize("names,change,settings,expected", [
    (("lab5-rules.md", "lab5-tools.md"), {"tools": ["off", "on"]}, {}, "lab5-tools.md"),
    (("lab5-rules.md", "lab5-tools.md"), {"rules": ["off", "on"]}, {}, "lab5-rules.md"),
    (("lab6-reviewer.md", "lab6-teams.md"), {"topology": ["single", "router_specialists"]}, {"topology": "router_specialists"}, "lab6-teams.md"),
    (("lab6-reviewer.md", "lab6-teams.md"), {"topology": ["a", "b"]}, {"topology": "router_specialists_reviewer"}, "lab6-reviewer.md"),
    (("l8-switch.md", "l8-trace.md"), {"trace_steps": ["off", "on"]}, {}, "l8-trace.md"),
    (("l8-switch.md", "l8-trace.md"), {"model_path": ["local", "hosted"]}, {}, "l8-switch.md"),
])
def test_each_labs_run_is_matched_by_its_change(names, change, settings, expected):
    files = _files(*names)
    assert gate.prediction_for(_rec("r1", 5, change=change, **settings), files, {}).name == expected


# ---- gate capstone ------------------------------------------------------------------------------------------------

def test_capstone_is_lab_nine():
    assert gate.parse_lab("capstone") == 9 and gate.parse_lab("Capstone") == 9
    assert gate.parse_lab("4") == 4 and gate.parse_lab("10") is None and gate.parse_lab("0") is None
    assert gate.parse_lab("x") is None


def test_gate_capstone_runs_the_lab_nine_checks(root, capsys, monkeypatch):
    monkeypatch.setattr(gate, "dirty_paths", lambda: [])
    monkeypatch.setattr(gate, "lab_records", lambda lab: [])
    monkeypatch.setattr(gate, "kept", lambda: {})
    monkeypatch.setattr(gate, "git", lambda *a, **k: "deadbeef")
    code = gate.main(["capstone"])
    out = capsys.readouterr().out
    assert code == 1 and "GATE lab 9" in out and "confirmation artifact" in out


def test_a_bad_lab_name_is_still_refused(capsys):
    assert gate.main(["ten"]) == 2

