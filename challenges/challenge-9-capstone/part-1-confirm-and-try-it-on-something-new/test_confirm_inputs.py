"""Capstone part 1: the confirmation and the pack copy.

Two layers. The first layer checks the checks themselves on fixed, hand-made records, so it runs anywhere and uses no
model and no reference number. The second layer runs the same checks on YOUR repository, and only runs in a learner
repository (one that has LAB-LOG.md at its root; the reference tree has none).

On the starter the second layer fails with: FileNotFoundError: runs/confirm-*.json
"""
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.cases import load_cases  # noqa: E402
from harness.confirm import majority_verdicts  # noqa: E402
from harness.pack_check import check_pack  # noqa: E402
from harness.schema import validate_confirm  # noqa: E402
from app.settings import DEFAULTS  # noqa: E402

LEARNER_REPO = (ROOT / "LAB-LOG.md").exists()
MEMO_KEYS = ["doc_id", "title", "audience", "owner_scope", "authority", "version_chain", "effective_from", "supersedes", "links"]


# ---- the checks ---------------------------------------------------------------------------------------------------

def check_confirmation(root: Path) -> str:
    """Raise AssertionError for the first problem with the newest runs/confirm-<id>.json; return its id."""
    files = sorted((root / "runs").glob("confirm-*.json")) if (root / "runs").exists() else []
    if not files:
        raise FileNotFoundError("runs/confirm-*.json: finish step 8 (python -m harness confirm) first")
    art = json.loads(files[-1].read_text(encoding="utf-8"))
    assert not validate_confirm(art), validate_confirm(art)
    sides = {"best": art["best"], "baseline": art["baseline"]}
    records = {}
    for name, side in sides.items():
        assert len(side["runs"]) == 3 and len(set(side["runs"])) == 3, f"{name}: three different runs are needed, got {side['runs']}"
        for rid in side["runs"]:
            rec = json.loads((root / "runs" / rid / "run.json").read_text(encoding="utf-8"))
            assert rec["status"] == "complete", f"{rid} is {rec['status']}"
            assert rec["cache_mode"] == "off", f"{rid} reused earlier replies (cache_mode {rec['cache_mode']})"
            assert rec["settings"] == side["settings"], f"{rid} has other settings than the rest of the {name} side"
            records[rid] = rec
    assert not set(sides["best"]["runs"]) & set(sides["baseline"]["runs"]), "a run is on both sides"
    trees = {r["manifest"]["code"]["tree"] for r in records.values()}
    assert len(trees) == 1 and art["baseline"]["rerun_on_current_code"], "the baseline was not rerun on today's code (use --from-run)"
    for key in ("corpus_hash", "question_set_version"):
        assert len({r["manifest"][key] for r in records.values()}) == 1, f"the six runs do not share one {key}"
    assert sides["best"]["settings"] != sides["baseline"]["settings"], "best and baseline are the same settings"
    assert art["comparison"]["comparable"], art["comparison"]["not_comparable_because"]
    assert set(art["must_pass_failures_seen"]) == {"best", "baseline"}
    return art["id"]


def check_mine_pack(pack_dir: Path, original_dir: Path) -> None:
    """Ten valid questions, a memo with its front matter, and the needs of step 6. Raises AssertionError."""
    problems = [m for s, m in check_pack(pack_dir.name, pack_dir=pack_dir, root=ROOT)
                if s == "FAIL" and "rows, expected" not in m]          # a copy holds ten questions, not 100
    assert not problems, problems
    original = {p.stem for p in (original_dir / "corpus").glob("*.md")}
    memos = [p for p in (pack_dir / "corpus").glob("*.md") if p.stem not in original]
    assert len(memos) == 1, f"the copy needs exactly one new memo, found {len(memos)}"
    meta = yaml.safe_load(memos[0].read_text(encoding="utf-8").split("---", 2)[1])
    assert [k for k in MEMO_KEYS if k not in meta] == [], "the memo front matter lacks " + ", ".join(k for k in MEMO_KEYS if k not in meta)
    cases = load_cases(pack_dir.name, pack_dir=pack_dir)
    extra = [c["case_id"] if "case_id" in c else c.get("id") for c in cases if c["kind"] != "question"]
    assert not extra, "the copy still holds attack or safety cases (delete eval/attacks.jsonl and empty eval/smoke.jsonl): " + ", ".join(map(str, extra[:3]))
    questions = [c for c in cases if c["kind"] == "question"]
    assert len(questions) == 10, f"{len(questions)} questions, expected ten"
    assert sum(1 for q in questions if memos[0].stem in q["gold_sources"]) >= 2, "at least two questions need the memo"
    assert any(q["expected_action"] == "tool" for q in questions), "at least one question needs a tool"
    assert any(q["expected_action"] == "handoff" for q in questions), "at least one question must go to a person"
    assert all(q["key_facts"] and q["gold_sources"] for q in questions if q["expected_action"] in ("answer", "tool")), \
        "every answer question needs key facts and gold sources"


# ---- layer 1: the checks on fixed, hand-made records --------------------------------------------------------------

def write_runs(root: Path, best_settings=None, base_settings=None, tree_for_base="T1", cache="off", base_rerun=True):
    best_settings = best_settings or {**DEFAULTS, "retriever": "hybrid"}
    base_settings = base_settings or {**DEFAULTS}
    ids = {"best": ["r011", "r012", "r013"], "baseline": ["r014", "r015", "r016"]}
    for side, settings, tree in (("best", best_settings, "T1"), ("baseline", base_settings, tree_for_base)):
        for rid in ids[side]:
            d = root / "runs" / rid
            d.mkdir(parents=True)
            (d / "run.json").write_text(json.dumps({"run_id": rid, "kind": "run", "status": "complete", "cache_mode": cache,
                                                    "settings": settings,
                                                    "manifest": {"code": {"tree": tree}, "corpus_hash": "c1", "question_set_version": "v1"}}),
                                        encoding="utf-8")
    art = {"id": "r011", "grader_version": "g", "created_at": "now", "mode": "all",
           "best": {"runs": ids["best"], "settings": best_settings, "answer_success": {"value": 0.7}, "cases": {}},
           "baseline": {"runs": ids["baseline"], "settings": base_settings, "answer_success": {"value": 0.6}, "cases": {},
                        "rerun_on_current_code": base_rerun},
           "comparison": {"comparable": True, "not_comparable_because": []}, "must_pass_failures_seen": {"best": {}, "baseline": {}}}
    (root / "runs" / "confirm-r011.json").write_text(json.dumps(art), encoding="utf-8")


def test_a_good_confirmation_passes(tmp_path):
    write_runs(tmp_path)
    assert check_confirmation(tmp_path) == "r011"


def test_no_confirmation_file_is_a_file_not_found_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="confirm-"):
        check_confirmation(tmp_path)


def test_a_reused_reply_is_caught(tmp_path):
    write_runs(tmp_path, cache="resume")
    with pytest.raises(AssertionError, match="reused earlier replies"):
        check_confirmation(tmp_path)


def test_a_baseline_on_old_code_is_caught(tmp_path):
    write_runs(tmp_path, tree_for_base="T0", base_rerun=False)
    with pytest.raises(AssertionError, match="today's code"):
        check_confirmation(tmp_path)


def test_best_and_baseline_must_differ(tmp_path):
    same = {**DEFAULTS}
    write_runs(tmp_path, best_settings=same, base_settings=same)
    with pytest.raises(AssertionError, match="same settings"):
        check_confirmation(tmp_path)


def verdict(passed, must=False):
    return {"m": {"answer_success": [1.0 if passed else 0.0, 1], "must_pass": [0.0 if passed else 1.0, 1] if must else [0, 0]},
            "context_tokens": None, "passed": passed, "timeout": False, "failure": None if passed else "wrong_fact", "must_pass": must}


def test_the_majority_decides_a_case_but_never_a_must_pass_failure():
    runs = [{"q-1": verdict(True), "q-2": verdict(True, must=True)},
            {"q-1": verdict(True), "q-2": verdict(True, must=True)},
            {"q-1": verdict(False), "q-2": verdict(False, must=True)}]
    out = majority_verdicts(runs)
    assert out["q-1"]["passed"] is True                              # two of three runs passed
    assert out["q-2"]["passed"] is False                             # a must-pass case passes only if every run passed it
    assert out["q-2"]["m"]["answer_success"] == [0.0, 1]


DOCS = {
    "doc-pricing": ("Pricing", "The Pro plan costs $38 per seat per month on monthly billing."),
    "doc-support": ("Support", "Pro support answers within 4 business hours."),
    "doc-memo-pilot": ("Pilot memo", "A pilot lasts 30 days and needs a signed order form before it starts."),
}
PRINCIPAL = {"id": "p-prospect", "role": "prospect", "verified": False, "account_id": None}


def question(i, text, gold, fact=None, action="answer"):
    return {"id": f"q-{i:03d}", "set": "mine", "wording": "plain", "principal": PRINCIPAL, "expected_action": action,
            "needs": ["retrieval"], "key_facts": [fact] if fact else [], "gold_sources": gold, "expected_tool": None,
            "must_pass": False, "slices": ["mine"],
            "steps": [{"id": "s1", "text": text, "principal": "p-prospect", "conversation": "c1", "request_id": "r1",
                       "expect": {"action": action}}]}


def write_pack(base: Path, name: str, with_memo: bool, questions: list):
    pd = base / name
    (pd / "corpus").mkdir(parents=True)
    (pd / "eval").mkdir()
    (pd / "tools").mkdir()
    for did, (title, body) in DOCS.items():
        if did == "doc-memo-pilot" and not with_memo:
            continue
        front = {"doc_id": did, "title": title, "audience": "public", "owner_scope": "everyone", "authority": "guide",
                 "version_chain": did, "effective_from": "2026-11-01", "supersedes": None, "links": []}
        (pd / "corpus" / f"{did}.md").write_text("---\n" + yaml.safe_dump(front) + "---\n# " + title + "\n\n" + body + "\n", encoding="utf-8")
    (pd / "eval" / "questions.jsonl").write_text("".join(json.dumps(q) + "\n" for q in questions), encoding="utf-8")
    (pd / "tools" / "fixture.json").write_text(json.dumps({"principals": [PRINCIPAL]}), encoding="utf-8")
    return pd


def ten_questions():
    pro = {"id": "f-pro", "entity": "Pro plan", "forms": ["$38"], "qualifiers": ["per month"]}
    pilot = {"id": "f-pilot", "entity": "pilot", "forms": ["30 days"], "qualifiers": []}
    qs = [question(1, "How long is a pilot?", ["doc-memo-pilot"], pilot), question(2, "What do I need before a pilot starts?", ["doc-memo-pilot"], pilot),
          question(3, "Pro price per month?", ["doc-pricing"], pro), question(4, "How fast is Pro support?", ["doc-support"],
                                                                               {"id": "f-sup", "entity": "Pro support", "forms": ["4 business hours"], "qualifiers": []}),
          question(5, "Book me a demo", ["doc-support"], {"id": "f-d", "entity": "Pro support", "forms": ["4 business hours"], "qualifiers": []}, "tool"),
          question(6, "I want to talk to a person", [], None, "handoff")]
    qs += [question(7 + i, f"Another question {i}", ["doc-pricing"], pro) for i in range(4)]
    return qs


def test_a_good_pack_copy_passes(tmp_path):
    original = write_pack(tmp_path, "mini", False, [])
    mine = write_pack(tmp_path, "mini-mine", True, ten_questions())
    check_mine_pack(mine, original)


def test_nine_questions_are_caught(tmp_path):
    original = write_pack(tmp_path, "mini", False, [])
    mine = write_pack(tmp_path, "mini-mine", True, ten_questions()[:9])
    with pytest.raises(AssertionError, match="expected ten"):
        check_mine_pack(mine, original)


def test_a_copy_without_a_memo_is_caught(tmp_path):
    original = write_pack(tmp_path, "mini", False, [])
    mine = write_pack(tmp_path, "mini-mine", False, [q for q in ten_questions() if "doc-memo-pilot" not in q["gold_sources"]] + ten_questions()[:2])
    with pytest.raises(AssertionError):
        check_mine_pack(mine, original)


def test_a_gold_source_outside_the_corpus_is_caught(tmp_path):
    original = write_pack(tmp_path, "mini", False, [])
    qs = ten_questions()
    qs[2]["gold_sources"] = ["doc-not-here"]
    mine = write_pack(tmp_path, "mini-mine", True, qs)
    with pytest.raises(AssertionError, match="doc-not-here"):
        check_mine_pack(mine, original)


# ---- layer 2: your own records (learner repositories only) --------------------------------------------------------

@pytest.mark.skipif(not LEARNER_REPO, reason="runs in a learner repository only")
def test_my_confirmation_file_and_six_runs():
    check_confirmation(ROOT)


@pytest.mark.skipif(not LEARNER_REPO, reason="runs in a learner repository only")
def test_my_pack_copy():
    mines = sorted((ROOT / "packs").glob("*-mine"))
    assert mines, "no packs/<your-pack>-mine/ folder yet (step 4)"
    check_mine_pack(mines[0], ROOT / "packs" / mines[0].name.removesuffix("-mine"))
