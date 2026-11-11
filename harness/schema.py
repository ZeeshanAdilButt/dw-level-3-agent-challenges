"""The shape of the files under runs/. A shipped check: the CI runs `python -m harness validate` on every commit."""
from . import config
from .records import digest_problems, load_results, run_path
from .util import read_json

COMMON = ["run_id", "kind", "started_at", "settings", "manifest", "grader_version", "prediction_commit"]
BY_KIND = {
    "screen": COMMON + ["overall", "slices", "retrieval_path", "ended_at", "chunks"],
    "run": COMMON + ["status", "parent", "change", "cache_mode", "model_path", "snapshot", "eligibility", "flags", "pack"],
}
MANIFEST_KEYS = ["code", "prompts", "corpus_hash", "index_settings", "model", "tool_fixtures", "grader_version",
                 "question_set_version", "fingerprint"]
RUN_COMPLETE_KEYS = ["totals", "metrics", "ended_at", "fingerprint"]
ROW_KEYS = ["id", "case_id", "kind", "slices", "passed", "failure_type", "steps", "spec", "result", "verdict"]


def validate_settings(s) -> list:
    errs = []
    if not isinstance(s, dict):
        return ["settings is not an object"]
    missing = [k for k in config.DEFAULTS if k not in s]
    if missing:
        errs.append("settings missing: " + ", ".join(missing))
    try:
        if not missing:
            config.validate(dict(s))
    except config.SettingsError as e:
        errs.append(str(e))
    return errs


def is_legacy(rec) -> bool:
    """Screen records written before the immutable-record format (no start time, no manifest). They are skipped."""
    return isinstance(rec, dict) and rec.get("kind") == "screen" and "started_at" not in rec and "manifest" not in rec


def validate_record(rec: dict) -> list:
    """Return the problems with a run.json record (an empty list means valid)."""
    if not isinstance(rec, dict):
        return ["record is not an object"]
    if is_legacy(rec):
        return []
    kind = rec.get("kind")
    if kind not in BY_KIND:
        return [f"unknown kind '{kind}' (expected screen or run)"]
    errs = [f"missing field '{k}'" for k in BY_KIND[kind] if k not in rec]
    errs += validate_settings(rec.get("settings"))
    m = rec.get("manifest")
    if isinstance(m, dict):
        errs += [f"manifest missing '{k}'" for k in MANIFEST_KEYS if k not in m]
    elif "manifest" in rec:
        errs.append("manifest is not an object")
    if kind == "run":
        if rec.get("cache_mode") not in ("resume", "off"):
            errs.append("cache_mode must be 'resume' or 'off'")
        if rec.get("status") not in ("running", "interrupted", "complete"):
            errs.append("status must be running, interrupted or complete")
        if rec.get("status") == "complete":
            errs += [f"complete run missing '{k}'" for k in RUN_COMPLETE_KEYS if k not in rec]
        if rec.get("eligibility") not in ("retrieval_only", "all"):
            errs.append("eligibility must be retrieval_only or all")
    return errs


def validate_confirm(rec: dict) -> list:
    errs = [f"confirm artifact missing '{k}'" for k in ("id", "best", "baseline", "comparison", "must_pass_failures_seen", "grader_version")
            if k not in rec]
    for side in ("best", "baseline"):
        s = rec.get(side)
        if isinstance(s, dict):
            errs += [f"{side} missing '{k}'" for k in ("runs", "settings", "answer_success", "cases") if k not in s]
    return errs


def validate_run_dir(run_id: str) -> list:
    errs = []
    rec = read_json(run_path(run_id) / "run.json")
    if rec is None:
        return [f"{run_id}: no run.json"]
    errs += [f"{run_id}: {e}" for e in validate_record(rec)]
    errs += digest_problems(run_id, rec)
    if rec.get("kind") == "run" and rec.get("status") == "complete":
        rows = load_results(run_id)
        if not rows:
            errs.append(f"{run_id}: cases.jsonl is empty")
        for row in rows:
            miss = [k for k in ROW_KEYS if k not in row]
            if miss:
                errs.append(f"{run_id}: case row {row.get('case_id')} missing {', '.join(miss)}")
                break
            for st in row["steps"]:
                if "eval" not in st or "reply" not in st:
                    errs.append(f"{run_id}: case {row['case_id']} step {st.get('step_id')} has no eval block or reply")
                    break
    if rec.get("kind") == "screen" and not (run_path(run_id) / "cases.jsonl").exists():
        errs.append(f"{run_id}: cases.jsonl missing")
    return errs
