"""python -m harness confirm: majority per case over repeated runs, for the best configuration and the baseline.

    python -m harness confirm --best r031 r032 r033 --baseline r034 r035 r036 [--id r031]

All runs of one side must share their settings. Stored outputs are regraded with today's graders. A case counts
as passed when more than half of the side's runs passed it, except cases flagged must_pass: those pass only when
every run passed, so a must-pass failure in any run is never erased by the majority and is always listed.
Writes runs/confirm-<id>.json; report links point into it (`runs/confirm-r031.json#best.answer_success`).
"""
import argparse
import sys
from collections import Counter

from . import signtest
from .diff import comparable, compare_verdicts, is_partial, regrade, selection
from .graders import GRADER_VERSION
from .metrics import aggregate
from .records import load_results, load_run
from .util import now_iso, write_json
from . import paths


def majority_verdicts(per_run: list) -> dict:
    """One synthetic verdict per case from several runs' verdicts (same case ids)."""
    out = {}
    ids = sorted(set().union(*[set(v) for v in per_run]))
    for cid in ids:
        vs = [r[cid] for r in per_run if cid in r]
        first = vs[0]
        m = {}
        for name in {k for v in vs for k in v["m"]}:
            entries = [v["m"].get(name, [0, 0]) for v in vs if v["m"].get(name, [0, 0])[1]]
            if not entries:
                m[name] = [0, 0]
                continue
            den = entries[0][1]
            nums = [e[0] for e in entries]
            if name == "must_pass":
                m[name] = [1.0 if any(n >= 1 for n in nums) else 0.0, den]  # a failure in any run stands
            elif all(n in (0, 1, 0.0, 1.0) for n in nums) and den == 1:
                m[name] = [1.0 if sum(nums) > len(nums) / 2 else 0.0, 1]
            else:
                m[name] = [sum(nums) / len(nums), den]
        toks = [v["context_tokens"] for v in vs if v.get("context_tokens") is not None]
        failing = [v for v in vs if v.get("failure")]
        passed_votes = sum(1 for v in vs if v.get("passed"))
        must = first["must_pass"]
        passed = (passed_votes == len(vs)) if must else (passed_votes > len(vs) / 2)
        if first.get("passed") is None:
            passed = None
        if must and any(v.get("passed") is False for v in vs):       # never erased by the majority
            for name in [k for k in m if k == "security" or k.startswith("security.") or k == "answer_success"]:
                if m[name][1]:
                    m[name] = [0.0, m[name][1]]
        out[cid] = {**first, "m": m, "context_tokens": (sum(toks) / len(toks)) if toks else None, "passed": passed,
                    "timeout": any(v["timeout"] for v in vs),
                    "failure": (Counter(v["failure"] for v in failing).most_common(1)[0][0]
                                if failing and passed is False else None)}
    return out


MIN_RUNS = 3
COST_KEYS = ("cost_p50", "cost_p95", "cost_total_usd", "latency_p50", "latency_p95", "hosted_equivalent_cost_p50",
             "hosted_equivalent_cost_p95", "hosted_equivalent_cost_total_usd", "calls_per_answer", "tokens_in", "tokens_out",
             "slowest_step")


def pooled_cost(run_ids: list, per_run: list) -> dict:
    """Cost, latency, calls, tokens and the slowest step of a side: every case of every run counted once (a majority
    has no cost of its own). Percentiles are over all the side's answers; totals are sums over its runs."""
    verdicts, results = [], []
    for rid, vs in zip(run_ids, per_run):
        for row in load_results(rid):
            key = f"{rid}:{row['case_id']}"
            results.append(dict(row["result"], case_id=key, steps=row["steps"]))
            if row["case_id"] in vs:
                verdicts.append({**vs[row["case_id"]], "case_id": key})
    pooled = aggregate(verdicts, results)
    out = {k: pooled[k] for k in COST_KEYS}
    out["cost_note"] = f"over all {len(run_ids)} runs of this side; totals are sums over the runs"
    return out


def side(run_ids: list, mode: str) -> tuple:
    if len(set(run_ids)) != len(run_ids):
        raise ValueError(f"a run is named twice in {' '.join(run_ids)}; each side needs separate runs")
    if len(run_ids) < MIN_RUNS:
        raise ValueError(f"{len(run_ids)} run(s) given ({' '.join(run_ids)}); each side needs at least {MIN_RUNS} runs")
    recs = [load_run(r) for r in run_ids]
    for r in recs:
        if r.get("kind") != "run" or r.get("status") != "complete":
            raise ValueError(f"{r['run_id']} is not a complete full run")
        if is_partial(r):
            raise ValueError(f"{r['run_id']} ran a subset of the cases ({selection(r)}); confirmation needs full runs")
    unsalted = [r["run_id"] for r in recs if not r.get("seed_salt")]
    if unsalted:
        raise ValueError(f"runs {' '.join(unsalted)} have no seed salt (a --url run or an edited record), so they are "
                         "not shown to be independent samples; confirm local runs made with --repeat")
    salts = [r["seed_salt"] for r in recs]
    if len(set(salts)) != len(salts):
        raise ValueError(f"runs {' '.join(run_ids)} share a seed salt, so they are not independent samples")
    first = recs[0]
    for r in recs[1:]:
        if r["settings"] != first["settings"]:
            raise ValueError(f"runs {run_ids[0]} and {r['run_id']} have different settings; one side must be one configuration")
    per_run = [regrade(r, mode) for r in run_ids]
    mv = majority_verdicts(per_run)
    seen = {}
    for rid, verdicts in zip(run_ids, per_run):
        for cid, v in verdicts.items():
            if v["must_pass"] and v.get("passed") is False:
                seen.setdefault(cid, []).append(rid)
    metrics = aggregate(list(mv.values()))
    metrics["failures_by_type"]["note"] = "majority outcome per case; the most common failure type among the failing runs"
    metrics.update(pooled_cost(run_ids, per_run))
    body = {"runs": run_ids, "settings": first["settings"], "code_tree": ((first.get("manifest") or {}).get("code") or {}).get("tree"),
            "per_run_answer_success": [aggregate(list(v.values()))["answer_success"] for v in per_run],
            "cases": {cid: v["passed"] for cid, v in mv.items()}, **metrics}
    return body, mv, seen, first


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harness confirm")
    ap.add_argument("runs", nargs="*", help="the best configuration's runs (or all runs, split in half, if --baseline is absent)")
    ap.add_argument("--best", nargs="+")
    ap.add_argument("--baseline", nargs="+")
    ap.add_argument("--id")
    a = ap.parse_args(argv)
    best, base = a.best or a.runs, a.baseline
    if not base and best and len(best) % 2 == 0 and not a.best:
        best, base = best[: len(best) // 2], best[len(best) // 2:]
    if not best or not base:
        print("error: give the best runs and the baseline runs: confirm --best r1 r2 r3 --baseline r4 r5 r6", file=sys.stderr)
        return 2
    try:
        recs = {r: load_run(r) for r in best + base}
        mode = "all" if any(r.get("eligibility") == "all" for r in recs.values()) else "retrieval_only"
        bbody, bmv, bseen, brec = side(best, mode)
        abody, amv, aseen, arec = side(base, mode)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    ok, reasons, diffs = comparable(brec, arec, one_change=False)     # best and baseline differ in many settings by design
    cmp = compare_verdicts(bmv, amv)
    cid = a.id or best[0]
    artifact = {
        "id": cid, "created_at": now_iso(), "grader_version": GRADER_VERSION, "mode": mode,
        "best": bbody, "baseline": {**abody, "rerun_on_current_code": abody["code_tree"] == bbody["code_tree"]},
        "comparison": {"baseline_named": base[0], "comparable": ok, "not_comparable_because": reasons, "changed_settings": diffs,
                       "answer_success": cmp["answer_success"], "security": cmp["security"]},
        "must_pass_failures_seen": {"best": bseen, "baseline": aseen},
    }
    out = paths.runs_dir() / f"confirm-{cid}.json"
    write_json(out, artifact)
    print(f"grader version {GRADER_VERSION}; wrote runs/{out.name}")
    for label, b in (("best", bbody), ("baseline", abody)):
        m = b["answer_success"]
        print(f"  {label}: runs {' '.join(b['runs'])}: answer success {m['display']} (n = {m['den']}) by majority; "
              f"security {b['security']['display']}; must-pass failures {b['must_pass']['display']}")
    e = cmp["answer_success"]
    print(f"  best against baseline {base[0]}: fixed {len(e['fixed'])}, broken {len(e['broken'])}, p = {e['p_text']}: "
          + (e["verdict"] if ok else "no verdict (not comparable: " + "; ".join(reasons) + ")"))
    for side_name, seen in (("best", bseen), ("baseline", aseen)):
        for cid2, rs in sorted(seen.items()):
            print(f"  must-pass failure seen in the {side_name} runs: {cid2} ({' '.join(rs)})")
    if not artifact["baseline"]["rerun_on_current_code"]:
        print("  note: the baseline runs used different code than the best runs; rerun the baseline with --from-run on today's code")
    return 0
