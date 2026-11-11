"""Capstone part 4: the rehearsal. The checks are tested on fixed, hand-made records, so they run anywhere with no model.
The second layer runs the same checks on YOUR rehearsal checkout, and only runs in a learner repository (one that has
LAB-LOG.md at its root; the reference tree has none).

On the starter the second layer fails with: FileNotFoundError: rehearsal/answers.md
"""
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LEARNER_REPO = (ROOT / "LAB-LOG.md").exists()
HEADINGS = [f"## Shape {i}" for i in range(1, 6)]


# ---- the checks ---------------------------------------------------------------------------------------------------

def check_answers(text: str) -> None:
    """Five headed answers in order, and a last line that starts `Time used:`. Raises AssertionError."""
    pos = [text.find(h) for h in HEADINGS]
    assert all(p >= 0 for p in pos), "missing headings: " + ", ".join(h for h, p in zip(HEADINGS, pos) if p < 0)
    assert pos == sorted(pos), "the headings are out of order"
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert lines and lines[-1].startswith("Time used:"), "the last line must start with 'Time used:'"


def shape_section(text: str, n: int) -> str:
    start = text.index(f"## Shape {n}") + len(f"## Shape {n}")
    nxt = text.find(f"## Shape {n + 1}", start)
    return text[start: nxt if nxt >= 0 else len(text)].strip()


def check_prediction_match(text: str, prediction: str) -> None:
    """The Shape 3 answer starts with the prediction text, word for word. Lines added after it are allowed."""
    section = " ".join(shape_section(text, 3).split())
    assert section.startswith(" ".join(prediction.split())), "the Shape 3 answer must start with the text of predictions/rehearsal.md"


def practice_smoke_runs(runs: list) -> list:
    return sorted((r for r in runs if r.get("flags", {}).get("smoke") and str(r.get("pack", "")).endswith("-practice")),
                  key=lambda r: r["started_at"])


def check_prediction_before_run(predicted_at: str, runs: list) -> None:
    smoke = practice_smoke_runs(runs)
    assert smoke, "no smoke run record on the practice pack yet"
    assert datetime.fromisoformat(predicted_at) < datetime.fromisoformat(smoke[0]["started_at"]), \
        "the prediction was committed after the first smoke run started"


def check_practice_copy(copy_dir: Path, original_dir: Path) -> None:
    new = sorted(p.name for p in (copy_dir / "corpus").glob("*.md") if not (original_dir / "corpus" / p.name).exists())
    assert len(new) == 1, f"the practice copy needs exactly one new document, found {len(new)}: {new}"
    changed = [p.name for p in (original_dir / "corpus").glob("*.md")
               if not (copy_dir / "corpus" / p.name).exists() or (copy_dir / "corpus" / p.name).read_bytes() != p.read_bytes()]
    assert not changed, f"the practice copy changed or dropped existing documents: {changed}"


def check_branches(runs: list, answers: str) -> str:
    smoke = practice_smoke_runs(runs)
    if len(smoke) >= 2:
        assert smoke[1].get("parent") == smoke[0]["run_id"], "the second smoke run must have the first as its parent"
        return "A"
    assert re.search(r"^Stopped by:\s*\S+", answers, re.M), "one smoke run only: add a 'Stopped by:' line naming the defence"
    return "B"


# ---- layer 1: the checks on fixed, hand-made records --------------------------------------------------------------

GOOD = "\n".join(f"{h}\nsome answer\n" for h in HEADINGS) + "\nTime used: 28 minutes"


def run(rid, pack, at, parent=None, smoke=True):
    return {"run_id": rid, "pack": pack, "started_at": at, "parent": parent, "flags": {"smoke": smoke}}


def make_pack(root: Path, name: str, docs: dict) -> Path:
    d = root / name / "corpus"
    d.mkdir(parents=True)
    for k, v in docs.items():
        (d / k).write_text(v, encoding="utf-8")
    return root / name


def test_five_headings_and_a_time_line_pass():
    check_answers(GOOD)


def test_a_missing_heading_is_caught():
    with pytest.raises(AssertionError, match="missing headings"):
        check_answers(GOOD.replace("## Shape 4", "## Shape four"))


def test_the_time_line_must_come_last():
    with pytest.raises(AssertionError, match="Time used"):
        check_answers(GOOD + "\nOne more thing.")


def test_shape_three_must_start_with_the_prediction():
    text = GOOD.replace("## Shape 3\nsome answer", "## Shape 3\nIt will end replies with a word. Family doc-injection.")
    check_prediction_match(text, "It will end replies with a word.\nFamily doc-injection.")
    with pytest.raises(AssertionError, match="Shape 3"):
        check_prediction_match(text, "A different prediction")


def test_a_prediction_before_the_first_smoke_run_passes():
    check_prediction_before_run("2026-11-01T10:00:00+00:00", [run("r1", "juniper-practice", "2026-11-01T10:05:00+00:00")])


def test_a_prediction_after_the_run_is_caught():
    with pytest.raises(AssertionError, match="after"):
        check_prediction_before_run("2026-11-01T10:10:00+00:00", [run("r1", "juniper-practice", "2026-11-01T10:05:00+00:00")])


def test_no_smoke_run_on_the_practice_pack_is_caught():
    with pytest.raises(AssertionError, match="no smoke run"):
        check_prediction_before_run("2026-11-01T10:00:00+00:00", [run("r1", "juniper", "2026-11-01T10:05:00+00:00")])


def test_one_new_document_passes(tmp_path):
    a = make_pack(tmp_path, "juniper", {"a.md": "x", "b.md": "y"})
    b = make_pack(tmp_path, "juniper-practice", {"a.md": "x", "b.md": "y", "poison.md": "z"})
    check_practice_copy(b, a)


def test_two_new_documents_are_caught(tmp_path):
    a = make_pack(tmp_path, "juniper", {"a.md": "x"})
    b = make_pack(tmp_path, "juniper-practice", {"a.md": "x", "p.md": "z", "q.md": "w"})
    with pytest.raises(AssertionError, match="exactly one"):
        check_practice_copy(b, a)


def test_an_edited_document_is_caught(tmp_path):
    a = make_pack(tmp_path, "juniper", {"a.md": "x"})
    b = make_pack(tmp_path, "juniper-practice", {"a.md": "changed", "p.md": "z"})
    with pytest.raises(AssertionError, match="changed or dropped"):
        check_practice_copy(b, a)


def test_branch_a_needs_the_first_run_as_parent():
    runs = [run("r1", "juniper-practice", "2026-11-01T10:05:00+00:00"),
            run("r2", "juniper-practice", "2026-11-01T10:20:00+00:00", parent="r1")]
    assert check_branches(runs, GOOD) == "A"
    runs[1]["parent"] = "r0"
    with pytest.raises(AssertionError, match="parent"):
        check_branches(runs, GOOD)


def test_branch_b_needs_a_stopped_by_line():
    runs = [run("r1", "juniper-practice", "2026-11-01T10:05:00+00:00")]
    with pytest.raises(AssertionError, match="Stopped by"):
        check_branches(runs, GOOD)
    assert check_branches(runs, GOOD + "\nStopped by: marking untrusted text") == "B"


# ---- layer 2: the checks on your own rehearsal checkout -----------------------------------------------------------

def first_commit_time(rel: str) -> str:
    """The time of the last commit that touched the file, so an edit made after the run fails the check."""
    out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", rel], cwd=ROOT, capture_output=True, text=True).stdout
    assert out.strip(), f"{rel} is not committed"
    return out.splitlines()[0]


@pytest.mark.skipif(not LEARNER_REPO, reason="runs in a learner repository only")
def test_your_rehearsal():
    answers_file = ROOT / "rehearsal" / "answers.md"
    if not answers_file.exists():
        raise FileNotFoundError("rehearsal/answers.md: write your answers first")
    answers = answers_file.read_text(encoding="utf-8")
    check_answers(answers)
    check_prediction_match(answers, (ROOT / "predictions" / "rehearsal.md").read_text(encoding="utf-8"))
    copies = sorted((ROOT / "packs").glob("*-practice"))
    assert len(copies) == 1, f"expected one packs/<company>-practice folder, found {len(copies)}"
    check_practice_copy(copies[0], ROOT / "packs" / copies[0].name[: -len("-practice")])
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "runs").glob("*/run.json"))]
    check_prediction_before_run(first_commit_time("predictions/rehearsal.md"), runs)
    check_branches(runs, answers)
