"""python -m harness run: execute the cases against the agent, grade the stored results, write the run record.

Steps: resolve settings (parent first, then --set) and print them; refuse uncommitted changes; copy the committed
tree to .cache/snapshots/<run_id>/ and execute from there (editing during a run changes nothing); store each
case's step results in runs/<run_id>/raw.jsonl; grade them with the current graders; write run.json and
cases.jsonl (case spec, stored steps, verdict).
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time

from . import config, paths
from .cases import load_cases, load_context
from .fingerprint import build_manifest, prediction_commit
from .graders import GRADER_VERSION, grade_case
from .graders.case import GAPS
from .metrics import aggregate, case_row, dashboard_totals, summary_table
from .records import all_runs, create_run_dir, load_results, record_digest
from .util import git, now_iso, read_json, read_jsonl, write_json, write_jsonl

IGNORED_DIRTY = ("runs/", ".cache/")


def add_arguments(ap):
    ap.add_argument("--pack", required=True)
    ap.add_argument("--set", action="append", default=[], metavar="key=value")
    ap.add_argument("--parent", help="start from this run's resolved settings (default: the last kept run)")
    ap.add_argument("--from-run", help="rerun this run's settings under today's code (confirmation baselines)")
    ap.add_argument("--repeat", type=int, default=1, help="N fresh runs; implies --no-cache")
    ap.add_argument("--no-cache", action="store_true", help="no reuse of earlier results (forced by --repeat)")
    ap.add_argument("--resume", action="store_true", help="continue the latest interrupted run with the same settings and code")
    ap.add_argument("--smoke", action="store_true", help="the 40 smoke cases (30 questions, 10 attacks)")
    ap.add_argument("--slice", dest="slice_name", help="only cases in this slice (or attack family)")
    ap.add_argument("--multi-change", action="store_true", help="mark a run that changes more than one setting")
    ap.add_argument("--retrieval-only", action="store_true", help="screen instead: no chat model")
    ap.add_argument("--url", help="chat with a deployed agent at this URL (the examiner's path)")
    ap.add_argument("--timeout", type=float, default=120, help="seconds per step")
    ap.add_argument("--label", default="")
    ap.add_argument("--yes", action="store_true", help="do not ask before a run that calls a paid hosted model")


def eligibility_mode(s: dict) -> str:
    """Labs 1 to 4 score the questions that need retrieval alone; from lab 5 (tools, rules, teams, defences) all."""
    return "all" if (s.get("tools") == "on" or s.get("rules") == "on" or s.get("topology") != "single" or s.get("defences")) else "retrieval_only"


# Calls per case (project brief, run manifest): single 1, with tools about 1.3, team 3, team with reviewer 4;
# the rules layer adds one classifier call per case.
CALLS_PER_CASE = {"single": 1.0, "router_specialists": 3.0, "router_specialists_reviewer": 4.0}
ASSUMED_TOKENS = (1500, 150)       # input and output tokens per call when no earlier run says otherwise


def estimate_hosted(settings: dict, n_cases: int, repeat: int = 1) -> dict:
    """{"calls", "usd", "model"} for a run on the hosted path; calls and dollars are estimates and say so."""
    from app.model import cost
    per = CALLS_PER_CASE.get(settings.get("topology"), 1.0)
    if settings.get("topology") == "single" and settings.get("tools") == "on":
        per = 1.3
    if settings.get("rules") == "on":
        per += 1.0
    calls = round(per * n_cases * repeat)
    model = settings.get("hosted_model") or "default-hosted"
    paid, _ = cost(model, ASSUMED_TOKENS[0], ASSUMED_TOKENS[1])
    return {"calls": calls, "usd": round(paid * calls, 4), "model": model}


def confirm_paid(settings: dict, n_cases: int, repeat: int, yes: bool, ask=input) -> bool:
    """Hosted runs cost money: print the call count and the estimate, then ask y unless --yes."""
    est = estimate_hosted(settings, n_cases, repeat)
    print(f"This run calls the hosted model {est['model']}: about {est['calls']} calls, an estimated ${est['usd']:.2f} "
          f"(a guess from {ASSUMED_TOKENS[0]} input and {ASSUMED_TOKENS[1]} output tokens per call and config/prices.toml).")
    if yes:
        print("--yes given: not asking.")
        return True
    try:
        answer = ask("Continue? [y/N] ").strip().lower()
    except EOFError:
        answer = ""
    return answer in ("y", "yes")


def dirty_paths() -> list:
    out = git("status", "--porcelain", "--untracked-files=all")
    if out is None:
        return ["<not a git repository>"]
    bad = []
    for line in out.splitlines():
        # git() strips the output, which eats the leading space of a first " M path" line, so the status code is
        # matched (one or two characters), not cut at a fixed width.
        m = re.match(r"^[ MADRCU?!]{1,2} (.*)$", line)
        path = (m.group(1) if m else line).strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ")[1]
        if not path.startswith(IGNORED_DIRTY):
            bad.append(path)
    return bad


def make_snapshot(run_id: str):
    """Copy the committed tree (HEAD) to .cache/snapshots/<run_id>/ and return its path."""
    dest = paths.root() / ".cache" / "snapshots" / run_id
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    tar = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=str(paths.root()), capture_output=True, timeout=300)
    if tar.returncode != 0:
        raise RuntimeError("git archive failed: " + tar.stderr.decode("utf-8", "replace"))
    with tarfile.open(fileobj=io.BytesIO(tar.stdout)) as tf:
        tf.extractall(dest)
    return dest


def find_resumable(settings: dict, commit: str):
    best = None
    for rec in all_runs():
        if rec.get("kind") == "run" and rec.get("status") in ("running", "interrupted") and rec.get("settings") == settings \
                and (rec.get("manifest") or {}).get("code", {}).get("commit") == commit:
            best = rec
    return best


def grade_run(run_id: str, run_dir, specs: list, raws: list, mode: str, ctx: dict):
    by = {r["case_id"]: r for r in raws}
    rows, verdicts, results = [], [], []
    for spec in specs:
        res = by.get(spec["id"])
        if res is None:
            res = {"case_id": spec["id"], "steps": [], "has_reply": False, "state_before": {}, "state_after": {}}
        v = grade_case(spec, res, ctx, mode=mode)
        verdicts.append(v)
        results.append(res)
        rows.append(case_row(spec, res, v))
    return rows, verdicts, results


def run_once(args, settings, parent, change, index=1, total=1) -> str:
    pd = paths.pack_dir(settings["pack"])
    mode = eligibility_mode(settings)
    cache_mode = "resume" if args.resume else "off"
    commit = git("rev-parse", "HEAD")
    resumed = find_resumable(settings, commit) if args.resume else None
    if args.resume and not resumed:
        print("note: no interrupted run with these settings and this code to resume; starting fresh")
        cache_mode = "off"
    cases = load_cases(settings["pack"], smoke=args.smoke, slice_name=args.slice_name)
    if not cases:
        raise SystemExit("error: no cases selected")
    if resumed:
        rid, rdir = resumed["run_id"], paths.runs_dir() / resumed["run_id"]
        print(f"resuming {rid}")
    else:
        rid, rdir = create_run_dir("r")
    started = resumed["started_at"] if resumed else now_iso()
    pred = prediction_commit()
    ctx = load_context(pd)
    snapshot = None
    if not args.url:
        snapshot = make_snapshot(rid)
    manifest = build_manifest(settings, pd)
    flags = {"multi_change": bool(args.multi_change), "smoke": bool(args.smoke), "slice": args.slice_name,
             "repeat_index": index, "repeat": total, "url": args.url}
    record = {"run_id": rid, "kind": "run", "label": args.label, "status": "running", "pack": settings["pack"],
              "parent": parent, "from_run": args.from_run, "change": change, "explicit_sets": sorted(config.parse_sets(args.set)),
              "settings": settings, "manifest": manifest,
              "prediction_commit": pred["commit"], "prediction_committed_at": pred["committed_at"],
              "cache_mode": cache_mode, "model_path": settings["model_path"],
              "snapshot": os.path.relpath(snapshot, paths.root()).replace("\\", "/") if snapshot else None,
              "eligibility": mode, "flags": flags, "started_at": started, "grader_version": GRADER_VERSION,
              "seed_salt": None if args.url else rid}     # salts every model seed, so repeated runs sample independently
    write_json(rdir / "run.json", record)
    write_json(rdir / "settings.json", settings)
    write_json(rdir / "context.json", ctx)
    write_jsonl(rdir / "specs.jsonl", cases)
    print(f"\n{rid}: {len(cases)} cases ({sum(c['kind'] == 'question' for c in cases)} questions, "
          f"{sum(c['kind'] == 'attack' for c in cases)} attacks), eligibility {mode}, grader {GRADER_VERSION}")
    t0 = time.time()
    if args.url:
        from .worker import execute
        os.environ.setdefault("DW_ROOT", str(paths.root()))
        info = execute(rdir, rid, url=args.url, timeout=args.timeout)
        ok = True
    else:
        env = dict(os.environ, DW_ROOT=str(snapshot), PYTHONPATH=str(snapshot) + os.pathsep + os.environ.get("PYTHONPATH", ""),
                   DW_CACHE=str(paths.root() / ".cache"), PYTHONIOENCODING="utf-8")
        proc = subprocess.run([sys.executable, "-m", "harness.worker", "--run-dir", str(rdir), "--run-id", rid,
                               "--timeout", str(args.timeout)], cwd=str(snapshot), env=env)
        ok = proc.returncode == 0
        info = read_json(rdir / "worker.json", {}) or {}
    raws = read_jsonl(rdir / "raw.jsonl")
    if not ok:
        record.update(status="interrupted", ended_at=now_iso())
        write_json(rdir / "run.json", record)
        print(f"error: the worker stopped after {len(raws)} of {len(cases)} cases; rerun with --resume to continue", file=sys.stderr)
        raise SystemExit(1)
    rows, verdicts, results = grade_run(rid, rdir, cases, raws, mode, ctx)
    metrics = aggregate(verdicts, results)
    write_jsonl(rdir / "cases.jsonl", rows)
    mocks = sorted({r.get("mock", "") for r in raws})
    record.update(status="complete", ended_at=now_iso(), seconds=round(time.time() - t0, 1), metrics=metrics, mock=mocks,
                  fingerprint=manifest["fingerprint"],
                  totals=dashboard_totals(metrics, {
                      "cases": len(cases), "questions": sum(c["kind"] == "question" for c in cases),
                      "attacks": sum(c["kind"] == "attack" for c in cases), "timeouts": sum(1 for v in verdicts if v["timeout"]),
                      "tokens_in": metrics["tokens_in"], "tokens_out": metrics["tokens_out"], "cost_usd": metrics["cost_total_usd"],
                      "embedding": (info or {}).get("embedding_stats")}))
    record["digest"] = record_digest(record, rows)
    write_json(rdir / "run.json", record)
    print(summary_table(metrics))
    print(f"  failures by type: {metrics['failures_by_type']}")
    for why in sorted(GAPS):
        print(f"  note: not written yet: {why}; every case it grades counts as failed")
    print(f"  hosted-equivalent cost p50 ${metrics['hosted_equivalent_cost_p50']['display']}, "
          f"calls per answer {metrics['calls_per_answer']['display']}")
    print(f"  cost p50 {metrics['cost_p50']['display']}, latency p50 {metrics['latency_p50']['display']} ms, "
          f"p95 {metrics['latency_p95']['display']} ms")
    return rid


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harness run")
    add_arguments(ap)
    args = ap.parse_args(argv)
    if args.repeat > 1:
        args.no_cache = True
    if args.no_cache and args.resume:
        print("error: --resume and --no-cache (or --repeat) cannot be used together", file=sys.stderr)
        return 2
    try:
        settings, parent, change = config.resolve(pack=args.pack, parent=args.parent, from_run=args.from_run,
                                                  sets=config.parse_sets(args.set))
    except config.SettingsError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(config.describe(settings, change))
    if args.multi_change and change is not None and len(change) < 2:
        print("note: --multi-change given but at most one setting differs from the parent")
    if change is not None and len(change) > 1 and not args.multi_change:
        print("warning: more than one setting differs from the parent; the run will not be comparable "
              "unless you pass --multi-change to mark it (and diff will say it is not a one-change comparison)")
    if args.retrieval_only:
        from . import screening
        sa = argparse.Namespace(pack=args.pack, set=args.set, parent=args.parent, label=args.label, chunker=None,
                                size=None, overlap=None, retriever=None)
        return screening.run_screen(sa)
    if not args.url:
        bad = dirty_paths()
        if bad:
            print("error: uncommitted changes stop the run (it executes from a snapshot of the committed tree):\n  "
                  + "\n  ".join(bad[:15]) + "\ncommit them, then run again.", file=sys.stderr)
            return 3
    if settings["model_path"] == "hosted" and not args.url:
        missing = [v for v in ("DW_HOSTED_BASE_URL", "DW_HOSTED_API_KEY") if not os.environ.get(v)]
        if missing:
            print("error: the hosted path needs " + " and ".join(missing) + " in the environment or in .env", file=sys.stderr)
            return 2
        n = len(load_cases(settings["pack"], smoke=args.smoke, slice_name=args.slice_name))
        if not confirm_paid(settings, n, args.repeat, args.yes):
            print("stopped: nothing was run")
            return 1
    ids = [run_once(args, settings, parent, change, i + 1, args.repeat) for i in range(args.repeat)]
    if args.repeat > 1:
        print("\nruns: " + " ".join(ids))
    return 0
