"""Comparability, diff, confirmation by majority, keep and revert, report-check: on synthetic run records."""
import json

import pytest

from conftest import PRO, make_result, make_spec, make_step
from harness import config, confirm, diff, keep, records, report_check
from harness.graders import GRADER_VERSION, grade_case
from harness.metrics import aggregate, case_row
from harness.util import read_json, write_json, write_jsonl

GOOD = "The Pro plan costs $38 per seat per month."
BAD = "I do not know."


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("DW_ROOT", str(tmp_path))
    (tmp_path / "runs").mkdir()
    return tmp_path


def settings(**over):
    s = dict(config.DEFAULTS)
    s.update(over)
    return s


def write_run(root, rid, outcomes, settings_=None, qset="q1", kind="run", mode="retrieval_only", must=(), parent=None,
              attacks=None, code_tree="t1", flags=None):
    """outcomes: {case_id: bool} for questions (True = a good reply). attacks: {case_id: bool leaked}."""
    rows = []
    for cid, good in outcomes.items():
        spec = make_spec(cid, key_facts=[PRO], gold=["d"], must_pass=cid in must)
        res = make_result([make_step(GOOD if good else BAD, citations=["d"], delivered_docs=["d"], ranked=["d#0"], delivered_ids=["d#0"],
                                     delivered_text=GOOD)])
        res["case_id"] = cid
        rows.append(case_row(spec, res, grade_case(spec, res, {}, mode)))
    for cid, leaked in (attacks or {}).items():
        spec = make_spec(cid, kind="attack", family="internal-content", pass_rule={"type": "no_text", "values": ["SECRET"]},
                         steps=[{"id": "s1", "text": "x", "expect": {}}])
        res = make_result([make_step("SECRET" if leaked else "no")])
        rows.append(case_row(spec, res, grade_case(spec, res, {}, mode)))
    d = root / "runs" / rid
    d.mkdir(parents=True)
    write_jsonl(d / "cases.jsonl", rows)
    write_json(d / "context.json", {})
    rec = {"run_id": rid, "kind": kind, "status": "complete", "pack": "quillon", "parent": parent, "from_run": None, "change": None,
           "settings": settings_ or settings(), "eligibility": mode, "flags": flags or {}, "started_at": "2026-11-01T10:00:00+00:00",
           "seed_salt": rid,
           "manifest": {"question_set_version": qset, "code": {"commit": "c", "tree": code_tree}, "grader_version": GRADER_VERSION}}
    write_json(d / "run.json", rec)
    return rec


# ---- comparability -----------------------------------------------------------------------------------------------

def rec(**kw):
    return {"kind": "run", "pack": "quillon", "settings": settings(**kw.pop("s", {})), "manifest": {"question_set_version": kw.pop("q", "q1")}, **kw}


def test_one_changed_setting_is_comparable():
    ok, why, diffs = diff.comparable(rec(), rec(s={"retriever": "hybrid"}))
    assert ok and diffs == ["retriever"]


def test_two_changed_settings_are_not_comparable():
    ok, why, _ = diff.comparable(rec(), rec(s={"retriever": "hybrid", "chunk_size": 200}))
    assert not ok and "2 settings differ" in why[0]


def test_a_rerun_of_the_same_settings_is_comparable():
    ok, _, diffs = diff.comparable(rec(), rec())
    assert ok and diffs == []


def test_the_model_may_be_the_one_change_but_not_with_another_setting():
    ok, _, diffs = diff.comparable(rec(), rec(s={"model_path": "hosted", "hosted_model": "small-1", "model": "qwen3:4b-instruct"}))
    assert ok and set(diffs) == {"model_path", "hosted_model"}
    ok, why, _ = diff.comparable(rec(), rec(s={"model_path": "hosted", "retriever": "hybrid"}))
    assert not ok and "model and other settings" in why[0]


def test_different_question_set_or_pack_is_not_comparable():
    assert not diff.comparable(rec(), rec(q="q2"))[0]
    assert not diff.comparable(rec(), rec(pack="juniper"))[0]


def test_screens_are_not_compared_by_verdict():
    assert not diff.comparable(rec(kind="screen"), rec())[0]


# ---- diff --------------------------------------------------------------------------------------------------------

def test_diff_counts_fixed_and_broken_and_names_the_baseline(root):
    base = {f"q-{i}": i % 2 == 0 for i in range(12)}                  # 6 good
    cand = dict(base)
    for i in (1, 3, 5, 7, 9, 11):
        cand[i and f"q-{i}"] = True                                     # fixes 6 ...
    cand["q-0"] = False                                                 # ... and breaks 1
    write_run(root, "r001", base)
    write_run(root, "r002", cand, settings_=settings(retriever="hybrid"), parent="r001")
    d = diff.diff_runs("r002", "r001")
    a = d["answer_success"]
    assert d["comparable"] and d["baseline"] == "r001" and d["grader_version"] == GRADER_VERSION
    assert (len(a["fixed"]), len(a["broken"]), a["ties"], a["n"]) == (6, 1, 5, 12)
    assert a["p_text"] == "0.125" and a["verdict"] == "inconclusive"   # 2 * (1 + 7) / 128


def test_diff_regrades_stored_outputs_with_the_current_graders(root):
    write_run(root, "r001", {"q-1": True, "q-2": True})
    # tamper with the stored verdict: diff must ignore it and grade the stored reply again
    rows = [json.loads(l) for l in (root / "runs/r001/cases.jsonl").read_text().splitlines()]
    rows[0]["verdict"]["m"]["answer_success"] = [0.0, 1]
    write_jsonl(root / "runs/r001/cases.jsonl", rows)
    assert diff.regrade("r001")["q-1"]["m"]["answer_success"] == [1.0, 1]


def test_diff_verdict_wording_improvement_and_harm(root):
    ids = [f"q-{i:02d}" for i in range(14)]
    write_run(root, "r001", {i: False for i in ids})
    write_run(root, "r002", {i: True for i in ids[:11]} | {i: False for i in ids[11:]}, settings_=settings(chunker="heading"))
    assert diff.diff_runs("r002", "r001")["answer_success"]["verdict"] == "evidence of improvement on this set"
    assert diff.diff_runs("r001", "r002")["answer_success"]["verdict"] == "evidence of harm"


def test_diff_attacks_are_a_separate_endpoint(root):
    write_run(root, "r001", {"q-1": True}, attacks={"a-1": True, "a-2": True, "a-3": False})
    write_run(root, "r002", {"q-1": True}, settings_=settings(rules="on"), mode="all", attacks={"a-1": False, "a-2": False, "a-3": False})
    d = diff.diff_runs("r002", "r001")
    assert d["answer_success"]["n"] == 1 and d["security"]["n"] == 3
    assert d["security"]["fixed"] == ["a-1", "a-2"] and d["security"]["broken"] == []


def test_diff_says_when_not_comparable(root):
    write_run(root, "r001", {"q-1": True})
    write_run(root, "r002", {"q-1": True}, settings_=settings(retriever="hybrid", chunk_size=200))
    d = diff.diff_runs("r002", "r001")
    assert not d["comparable"] and d["not_comparable_because"]


# ---- confirmation ------------------------------------------------------------------------------------------------

def test_majority_per_case_and_a_must_pass_failure_is_never_erased(root):
    s_best, s_base = settings(retriever="hybrid"), settings()
    cases = ["q-1", "q-2", "q-3", "q-4"]
    # q-1 good in 2 of 3 (majority pass); q-2 good in 1 of 3 (majority fail); q-3 is must-pass, good in 2 of 3
    runs = {"r010": {"q-1": True, "q-2": True, "q-3": True, "q-4": True},
            "r011": {"q-1": True, "q-2": False, "q-3": True, "q-4": True},
            "r012": {"q-1": False, "q-2": False, "q-3": False, "q-4": True}}
    for rid, o in runs.items():
        write_run(root, rid, o, settings_=s_best, must={"q-3"})
    for rid in ("r020", "r021", "r022"):
        write_run(root, rid, {c: False for c in cases}, settings_=s_base, must={"q-3"})
    assert confirm.main(["--best", "r010", "r011", "r012", "--baseline", "r020", "r021", "r022", "--id", "r010"]) == 0
    art = read_json(root / "runs/confirm-r010.json")
    best = art["best"]
    assert best["cases"] == {"q-1": True, "q-2": False, "q-3": False, "q-4": True}      # q-3 fails: one run failed a must-pass case
    assert best["answer_success"]["num"] == 2 and best["answer_success"]["den"] == 4 and best["answer_success"]["display"] == "50.0%"
    assert art["must_pass_failures_seen"]["best"] == {"q-3": ["r012"]}
    assert set(art["must_pass_failures_seen"]["baseline"]) == {"q-3"}
    assert best["must_pass"]["failed_ids"] == ["q-3"]
    assert art["comparison"]["baseline_named"] == "r020" and art["grader_version"] == GRADER_VERSION
    assert art["baseline"]["rerun_on_current_code"] is True
    assert art["comparison"]["answer_success"]["fixed"] == ["q-1", "q-4"]


def test_confirm_compares_a_best_setup_that_kept_several_settings_with_the_baseline(root):
    s_best = settings(chunker="heading", retriever="hybrid", context="section_parent", tools="on", model_path="stub")
    for rid in ("r010", "r011", "r012"):
        write_run(root, rid, {"q-1": True, "q-2": True}, settings_=s_best)
    for rid in ("r020", "r021", "r022"):
        write_run(root, rid, {"q-1": False, "q-2": False})
    assert confirm.main(["--best", "r010", "r011", "r012", "--baseline", "r020", "r021", "r022"]) == 0
    cmp = read_json(root / "runs/confirm-r010.json")["comparison"]
    assert cmp["comparable"] is True and cmp["not_comparable_because"] == []
    assert set(cmp["changed_settings"]) == {"chunker", "retriever", "context", "tools", "model_path"}
    assert cmp["answer_success"]["fixed"] == ["q-1", "q-2"]
    write_run(root, "r030", {"q-1": True}, qset="q2")                      # a different question set still has no verdict
    write_run(root, "r031", {"q-1": True}, qset="q2")
    write_run(root, "r032", {"q-1": True}, qset="q2")
    assert confirm.main(["--best", "r030", "r031", "r032", "--baseline", "r020", "r021", "r022"]) == 0
    assert read_json(root / "runs/confirm-r030.json")["comparison"]["comparable"] is False


def test_diff_still_allows_one_change_only():
    assert not diff.comparable(rec(), rec(s={"retriever": "hybrid", "chunk_size": 200}), one_change=True)[0]
    assert diff.comparable(rec(), rec(s={"retriever": "hybrid", "chunk_size": 200}), one_change=False)[0]


def test_confirm_refuses_a_side_with_mixed_settings(root, capsys):
    for rid in ("r001", "r003", "r004", "r005", "r006"):
        write_run(root, rid, {"q-1": True})
    write_run(root, "r002", {"q-1": True}, settings_=settings(top_k=3))
    assert confirm.main(["--best", "r001", "r002", "r003", "--baseline", "r004", "r005", "r006"]) == 2
    assert "different settings" in capsys.readouterr().err


def test_majority_of_two_runs_needs_both(root):
    a = {"q-1": grade_case(make_spec("q-1", key_facts=[PRO]), make_result([make_step(GOOD)]), {}, "all")}
    b = {"q-1": grade_case(make_spec("q-1", key_facts=[PRO]), make_result([make_step(BAD)]), {}, "all")}
    assert confirm.majority_verdicts([a, b])["q-1"]["m"]["answer_success"] == [0.0, 1]       # 1 of 2 is not a majority


def test_aggregate_empty_sets_are_dashes_and_zero_of_zero():
    m = aggregate([])
    assert m["answer_success"]["display"] == "-" and m["answer_success"]["value"] is None
    assert m["must_pass"]["display"] == "0 of 0" and m["over_refusal"]["display"] == "0 of 0"
    assert m["failures_by_type"]["timeout"] == 0 and list(m["failures_by_type"])[:3] == ["timeout", "hard_rule_broken", "leak"]


def test_percentiles_nearest_rank_and_p95_needs_twenty():
    from harness.util import percentile
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50) == 5
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95) == 10
    results = [{"case_id": f"c{i}", "has_reply": True, "cost_usd": 0.01 * i, "latency_ms": 100.0 * i, "steps": []} for i in range(1, 11)]
    verdicts = [{"case_id": r["case_id"], "m": {}, "kind": "question", "family": None} for r in results]
    out = aggregate(verdicts, results)
    assert out["latency_p50"]["value"] == 500.0 and out["latency_p95"]["value"] is None       # n = 10 is below 20


# ---- keep and revert ---------------------------------------------------------------------------------------------

def test_keep_and_revert_update_kept_json_and_settings_toml_together(root):
    (root / "config").mkdir()
    (root / "config" / "settings.toml").write_text('# mine\n[lab2]\nchunker = "fixed"\nchunk_size = 400\n[lab3]\nretriever = "bm25"\n', encoding="utf-8")
    write_run(root, "r001", {"q-1": True})
    write_run(root, "r002", {"q-1": True}, settings_=settings(retriever="hybrid", chunk_size=300), parent="r001")
    assert keep.main(["r001"]) == 0
    assert keep.main(["r002"]) == 0
    assert read_json(root / "runs/kept.json") == {"run_id": "r002"}          # exactly what the dashboard reads
    toml = (root / "config/settings.toml").read_text(encoding="utf-8")
    assert records.kept()["kept"] == "r002" and 'retriever = "hybrid"' in toml and "chunk_size = 300" in toml and "[lab3]" in toml
    assert "# mine" in toml
    assert keep.main_revert([]) == 0
    assert read_json(root / "runs/kept.json") == {"run_id": "r001"}
    kept = records.kept()
    toml = (root / "config/settings.toml").read_text(encoding="utf-8")
    assert kept["kept"] == "r001" and kept["reverted"] == "r002" and 'retriever = "bm25"' in toml and "chunk_size = 400" in toml
    assert [d["action"] for d in kept["decisions"]] == ["keep", "keep", "revert"]
    assert keep.main_revert([]) == 2          # nothing earlier to return to


def test_keep_refuses_a_screen_and_creates_settings_toml_when_missing(root):
    write_run(root, "s001", {"q-1": True}, kind="screen")
    assert keep.main(["s001"]) == 2
    write_run(root, "r001", {"q-1": True}, settings_=settings(top_k=3))
    assert keep.main(["r001"]) == 0
    assert "top_k = 3" in (root / "config/settings.toml").read_text(encoding="utf-8")


def test_resolve_loads_the_kept_run_then_applies_set(root):
    write_run(root, "r001", {"q-1": True}, settings_=settings(chunker="heading", chunk_size=300))
    assert keep.main(["r001"]) == 0
    s, parent, change = config.resolve(pack="quillon", sets=config.parse_sets(["retriever=hybrid"]))
    assert parent == "r001" and s["chunker"] == "heading" and s["chunk_size"] == 300 and s["retriever"] == "hybrid"
    assert change == {"retriever": ["bm25", "hybrid"]}
    s2, parent2, _ = config.resolve(pack="quillon", parent="r001", sets={"chunk_size": 250})
    assert s2["chunk_size"] == 250 and parent2 == "r001"


def test_settings_validation_and_coercion():
    with pytest.raises(config.SettingsError):
        config.validate({**config.DEFAULTS, "overlap": 400})
    with pytest.raises(config.SettingsError):
        config.parse_sets(["nonsense=1"])
    assert config.parse_sets(["top_k=3", "defences=access,marking", "temperature=0.5"]) == {
        "top_k": 3, "defences": ["access", "marking"], "temperature": 0.5}


# ---- report-check ------------------------------------------------------------------------------------------------

def make_confirm(root):
    write_json(root / "runs" / "confirm-r031.json", {"best": {"answer_success": {"value": 0.64, "num": 64, "den": 100},
                                                              "must_pass": {"value": 0.0, "num": 0, "den": 8}, "runs": ["r1", "r2"]}})


def test_report_links_match_the_artifact(root):
    make_confirm(root)
    md = "We reach [64% answer success](runs/confirm-r031.json#best.answer_success) on 100 questions."
    problems, n, words = report_check.check_text(md, root)
    assert problems == [] and n == 1


def test_report_link_with_a_wrong_number_or_missing_target_fails(root):
    make_confirm(root)
    bad = report_check.check_text("[65% answer success](runs/confirm-r031.json#best.answer_success)", root)[0]
    assert len(bad) == 1 and "0.64" in bad[0]
    missing = report_check.check_text("[64% x](runs/confirm-r031.json#best.nope)", root)[0]
    assert "has no 'best.nope'" in missing[0]
    nofile = report_check.check_text("[64% x](runs/confirm-r099.json#best.answer_success)", root)[0]
    assert "does not exist" in nofile[0]


def test_report_percentage_rounding_and_decimals(root):
    make_confirm(root)
    assert not report_check.check_text("[64.0% a](runs/confirm-r031.json#best.answer_success)", root)[0]
    assert report_check.check_text("[63.9% a](runs/confirm-r031.json#best.answer_success)", root)[0]
    assert not report_check.check_text("[0.64 a](runs/confirm-r031.json#best.answer_success)", root)[0]
    assert not report_check.check_text("[0 of 8 must-pass failures](runs/confirm-r031.json#best.must_pass)", root)[0]


def test_report_word_limit_counts_link_text_and_skips_urls(root):
    make_confirm(root)
    ok = "word " * 598 + "[64% answer success](runs/confirm-r031.json#best.answer_success)"       # 598 + 3 = 601
    problems, _, words = report_check.check_text(ok, root)
    assert words == 601 and any("601 words" in p for p in problems)
    fine = "word " * 597 + "[64% answer success](runs/confirm-r031.json#best.answer_success)"      # 600
    assert report_check.check_text(fine, root)[0] == []


def test_unlinked_numbers_are_not_checked(root):
    assert report_check.check_text("We chose chunk size 300 and kept 4 of 5 ideas.", root)[0] == []


def test_confirm_refuses_the_same_run_twice_or_runs_that_share_a_seed_salt(root, capsys):
    for rid in ("r001", "r002", "r003", "r004", "r005", "r006"):
        write_run(root, rid, {"q-1": True})
    best, base = ["--best", "r001", "r002", "r003"], ["--baseline", "r004", "r005", "r006"]
    assert confirm.main(["--best", "r001", "r001", "r002", *base]) == 2                            # one run named twice
    for rid in ("r001", "r002"):
        rec = read_json(root / "runs" / rid / "run.json")
        write_json(root / "runs" / rid / "run.json", {**rec, "seed_salt": "same"})
    assert confirm.main([*best, *base]) == 2                                                       # not independent samples
    assert "share a seed salt" in capsys.readouterr().err


def test_confirm_needs_three_salted_full_runs_a_side(root, capsys):
    for rid in ("r001", "r002", "r003", "r004", "r005", "r006"):
        write_run(root, rid, {"q-1": True})
    base = ["--baseline", "r004", "r005", "r006"]
    assert confirm.main(["--best", "r001", "--baseline", "r004"]) == 2                              # one run a side
    assert "at least 3 runs" in capsys.readouterr().err
    assert confirm.main(["--best", "r001", "r002", *base]) == 2
    for salt in (None, ""):                                                                          # a --url run or an edited record
        rec = read_json(root / "runs" / "r001" / "run.json")
        write_json(root / "runs" / "r001" / "run.json", {**rec, "seed_salt": salt})
        assert confirm.main(["--best", "r001", "r002", "r003", *base]) == 2
        assert "no seed salt" in capsys.readouterr().err
    write_run(root, "r007", {"q-1": True}, flags={"smoke": True})
    write_run(root, "r008", {"q-1": True}, flags={"slice": "tool"})
    for partial in ("r007", "r008"):
        assert confirm.main(["--best", partial, "r002", "r003", *base]) == 2
        assert "subset of the cases" in capsys.readouterr().err
    write_run(root, "r009", {"q-1": True})
    assert confirm.main(["--best", "r002", "r003", "r009", *base]) == 0


def test_confirm_reports_cost_and_latency_over_all_runs_of_a_side(root):
    for i, rid in enumerate(("r001", "r002", "r003", "r004", "r005", "r006")):
        write_run(root, rid, {"q-1": True, "q-2": True})
        path = root / "runs" / rid / "cases.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        for j, row in enumerate(rows):
            row["result"].update(cost_usd=0.01 * (i + 1), latency_ms=100.0 * (i + j + 1), calls=2, tokens_in=10, tokens_out=3)
        write_jsonl(path, rows)
    assert confirm.main(["--best", "r001", "r002", "r003", "--baseline", "r004", "r005", "r006"]) == 0
    art = read_json(root / "runs/confirm-r001.json")
    for key in confirm.COST_KEYS:
        assert key in art["best"] and key in art["baseline"], key
    assert art["best"]["latency_p50"]["value"] == 200.0 and art["best"]["latency_p50"]["n"] == 6       # 100 200 200 300 300 400
    assert art["best"]["cost_total_usd"] == 0.12 and art["best"]["tokens_in"] == 60
    assert art["best"]["calls_per_answer"]["value"] == 2.0


def test_keep_refuses_a_smoke_or_slice_run(root, capsys):
    write_run(root, "r001", {"q-1": True}, flags={"smoke": True})
    write_run(root, "r002", {"q-1": True}, flags={"slice": "tool"})
    for rid in ("r001", "r002"):
        assert keep.main([rid]) == 2
        assert "only a full run can be kept" in capsys.readouterr().err
    assert not (root / "runs" / "kept.json").exists()


def test_diff_never_compares_a_smoke_run_with_a_full_run(root):
    write_run(root, "r001", {"q-1": False, "q-2": False})
    write_run(root, "r002", {"q-1": True}, settings_=settings(retriever="hybrid"), flags={"smoke": True})
    d = diff.diff_runs("r002", "r001")
    assert not d["comparable"] and "different case selections (smoke and full)" in d["not_comparable_because"]
    write_run(root, "r003", {"q-1": False}, flags={"smoke": True})
    assert diff.diff_runs("r002", "r003")["comparable"]                     # two smoke runs cover the same cases


def test_report_numbers_in_a_metric_name_are_not_the_measured_value(root):
    write_json(root / "runs" / "confirm-r031.json", {"best": {"recall5": {"value": 0.72}, "mrr": {"value": 0.64},
                                                              "latency_p50": {"value": 310.0}, "cost_p95": {"value": 0.02},
                                                              "recall3": {"value": 0.5}}})
    good = ["[recall at 5: 72.0%](runs/confirm-r031.json#best.recall5)", "[MRR at 5: 0.640](runs/confirm-r031.json#best.mrr)",
            "[p50 latency 310 ms](runs/confirm-r031.json#best.latency_p50)", "[p95 cost $0.02](runs/confirm-r031.json#best.cost_p95)",
            "[recall5 72%](runs/confirm-r031.json#best.recall5)", "[top 3 recall 50%](runs/confirm-r031.json#best.recall3)"]
    for md in good:
        assert report_check.check_text(md, root)[0] == [], md
    for md in ("[recall at 5: 75.0%](runs/confirm-r031.json#best.recall5)", "[p50 latency 300 ms](runs/confirm-r031.json#best.latency_p50)",
               "[recall at 5](runs/confirm-r031.json#best.recall5)"):
        assert report_check.check_text(md, root)[0], md


def test_report_zero_is_shown_only_for_a_value_that_is_zero(root):
    write_json(root / "runs" / "confirm-r031.json", {"best": {"small": {"value": 0.3}, "rate": {"value": 0.004},
                                                              "none": {"value": 0.0, "num": 0, "den": 8}}})
    assert report_check.check_text("[0 failures](runs/confirm-r031.json#best.small)", root)[0]
    assert report_check.check_text("[0% leaked](runs/confirm-r031.json#best.rate)", root)[0]
    assert report_check.check_text("[0.4% leaked](runs/confirm-r031.json#best.rate)", root)[0] == []
    assert report_check.check_text("[0 of 8 must-pass failures](runs/confirm-r031.json#best.none)", root)[0] == []
    assert report_check.check_text("[0.0% leaked](runs/confirm-r031.json#best.none)", root)[0] == []


def test_a_change_that_switches_eligibility_is_compared_on_the_same_cases(root):
    # q-2 needs a tool: scored only in "all". The parent (retrieval only) and the tools run are both regraded in "all".
    write_run(root, "r001", {"q-1": True, "q-2": False})
    write_run(root, "r002", {"q-1": True, "q-2": True}, settings_=settings(tools="on"), mode="all", parent="r001")
    for d in (root / "runs" / "r001", root / "runs" / "r002"):
        rows = [json.loads(line) for line in (d / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
        rows[1]["spec"]["needs"] = ["tool"]
        write_jsonl(d / "cases.jsonl", rows)
    d = diff.diff_runs("r002", "r001")
    assert d["comparable"] and d["mode"] == "all" and d["changed_settings"] == ["tools"]
    assert d["answer_success"]["n"] == 2 and d["answer_success"]["fixed"] == ["q-2"]
    same = rec(eligibility="all"), rec(eligibility="retrieval_only")                # no change, different modes: edited
    ok, why, _ = diff.comparable(*same)
    assert not ok and "different eligibility modes" in why
