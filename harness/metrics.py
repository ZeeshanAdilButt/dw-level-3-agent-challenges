"""Aggregate case verdicts into the metrics table of the notes (section 3).

Every metric is {"value", "num", "den", "n", "display"}. An empty eligible set gives value None and the display
"-" (not applicable) for ratios, and "0 of 0" for counts (must-pass failures, over-refusals).
"""
from collections import Counter

from .graders import FAILURE_ORDER
from .util import percentile

RATIOS = ["answer_success", "cited_correctly", "recall5", "recall3", "mrr", "span_coverage", "citation_precision",
          "grounded", "context_fact_recall", "tool_correctness", "handoff_correctness", "false_handoff",
          "clarify_correctness", "false_clarify", "security"]
COUNTS = ["must_pass", "over_refusal"]


def _metric(num, den, count=False, digits=1):
    if den == 0:
        return {"value": None, "num": 0, "den": 0, "n": 0, "display": "0 of 0" if count else "-"}
    value = num / den
    shown = f"{round(num)} of {den}" if count else f"{100 * value:.{digits}f}%"
    return {"value": round(value, 6), "num": round(num, 6), "den": den, "n": den, "display": shown}


def _pctile(values, p, min_n=0):
    if not values or len(values) < min_n:
        return {"value": None, "n": len(values), "display": "-"}
    return {"value": percentile(values, p), "n": len(values), "display": f"{percentile(values, p):g}"}


def aggregate(verdicts: list, results: list = None) -> dict:
    """`verdicts` from graders.grade_case; `results` (the stored case results) for cost, latency and spans."""
    out = {}
    for name in RATIOS + COUNTS:
        num = sum(v["m"].get(name, [0, 0])[0] for v in verdicts)
        den = sum(v["m"].get(name, [0, 0])[1] for v in verdicts)
        out[name] = _metric(num, den, count=name in COUNTS)
    if out["mrr"]["value"] is not None:
        out["mrr"]["display"] = f"{out['mrr']['value']:.3f}"
    # recall, MRR and the like are means of per-question values, which num/den already is (den counts questions)
    families = sorted({v["family"] for v in verdicts if v.get("family")})
    out["security_by_family"] = {
        f: _metric(sum(v["m"].get(f"security.{f}", [0, 0])[0] for v in verdicts),
                   sum(v["m"].get(f"security.{f}", [0, 0])[1] for v in verdicts)) for f in families}
    out["must_pass"]["failed_ids"] = [v["case_id"] for v in verdicts if v["m"].get("must_pass", [0, 0])[0] >= 1]
    toks = [v["context_tokens"] for v in verdicts if v.get("context_tokens") is not None]
    out["context_tokens"] = {"mean": round(sum(toks) / len(toks), 1) if toks else None, "n": len(toks),
                             "p95": _pctile(toks, 95, 20)["value"], "display": f"{sum(toks) / len(toks):.0f}" if toks else "-"}
    failed = [v for v in verdicts if v.get("failure")]
    counts = Counter(v["failure"] for v in failed)
    out["failures_by_type"] = {t: counts.get(t, 0) for t in FAILURE_ORDER}
    out["failures_by_type"]["total_failed"] = len(failed)
    out["classifier_recall"] = {"value": None, "n": 0, "display": "-", "note": "diagnostic set, measured apart from the run"}
    if results is not None:
        by_id = {r["case_id"]: r for r in results}
        costs = [by_id[v["case_id"]].get("cost_usd", 0.0) for v in verdicts if v["case_id"] in by_id and by_id[v["case_id"]].get("has_reply")]
        lats = [by_id[v["case_id"]].get("latency_ms") for v in verdicts if v["case_id"] in by_id and by_id[v["case_id"]].get("has_reply")]
        lats = [x for x in lats if x is not None]
        out["cost_p50"], out["cost_p95"] = _pctile(costs, 50), _pctile(costs, 95, 20)
        out["latency_p50"], out["latency_p95"] = _pctile(lats, 50), _pctile(lats, 95, 20)
        replied = [by_id[v["case_id"]] for v in verdicts if v["case_id"] in by_id and by_id[v["case_id"]].get("has_reply")]
        equiv = [r.get("hosted_equivalent_usd", 0.0) for r in replied]
        out["hosted_equivalent_cost_p50"], out["hosted_equivalent_cost_p95"] = _pctile(equiv, 50), _pctile(equiv, 95, 20)
        out["hosted_equivalent_cost_total_usd"] = round(sum(r.get("hosted_equivalent_usd", 0.0) for r in results), 6)
        calls = [r.get("calls", 0) for r in replied]
        out["calls_per_answer"] = {"value": round(sum(calls) / len(calls), 3) if calls else None, "n": len(calls),
                                   "display": f"{sum(calls) / len(calls):.2f}" if calls else "-"}
        out["tokens_in"] = sum(r.get("tokens_in", 0) for r in results)
        out["tokens_out"] = sum(r.get("tokens_out", 0) for r in results)
        out["cost_total_usd"] = round(sum(r.get("cost_usd", 0.0) for r in results), 6)
        out["slowest_step"] = slowest_step(results)
    return out


def slowest_step(results: list) -> dict:
    """The child span (a span whose parent is a case-level root span) with the greatest median inclusive duration.

    Nested spans are never compared with their own parent: only direct children of a root span are candidates."""
    durations = {}
    for r in results:
        for s in r.get("steps") or []:
            spans = (s.get("eval") or {}).get("spans") or []
            roots = {sp["span_id"] for sp in spans if not sp.get("parent_id")}
            for sp in spans:
                if sp.get("parent_id") in roots:
                    durations.setdefault(sp["name"], []).append(sp["end_ms"] - sp["start_ms"])
    if not durations:
        return {"name": None, "median_ms": None, "n": 0, "display": "-"}
    med = {n: percentile(v, 50) for n, v in durations.items()}
    name = max(sorted(med), key=lambda n: med[n])
    return {"name": name, "median_ms": med[name], "n": len(durations[name]), "display": f"{name} {med[name]:.0f} ms"}


def summary_table(metrics: dict) -> str:
    rows = [("answer success", "answer_success"), ("cited correctly", "cited_correctly"), ("recall at 5", "recall5"),
            ("recall at 3", "recall3"), ("MRR at 5", "mrr"), ("evidence-span coverage", "span_coverage"),
            ("citation precision", "citation_precision"), ("grounded", "grounded"),
            ("context fact recall", "context_fact_recall"), ("security pass rate", "security"),
            ("tool correctness", "tool_correctness"), ("handoff correctness", "handoff_correctness"),
            ("false handoff rate", "false_handoff"), ("clarify correctness", "clarify_correctness"),
            ("false clarify rate", "false_clarify"), ("must-pass failures", "must_pass"), ("over-refusals", "over_refusal")]
    lines = []
    for label, key in rows:
        m = metrics[key]
        if m["den"] == 0 and key in ("tool_correctness", "handoff_correctness", "false_handoff", "clarify_correctness",
                                     "false_clarify", "over_refusal", "span_coverage", "grounded"):
            continue
        lines.append(f"  {label:26s} {m['display']:>9s}  (n = {m['den']})")
    return "\n".join(lines)


def _vn(m):
    return {"value": m["value"], "n": m["den"], "num": m["num"], "den": m["den"]}


def dashboard_totals(metrics: dict, counts: dict) -> dict:
    """The metrics under the names dashboard/lib.js reads from run.json `totals` ({value, n} each), plus counts."""
    t = dict(counts)
    for name, key in (("answer_success", "answer_success"), ("cited_correctly", "cited_correctly"), ("recall5", "recall5"),
                      ("recall3", "recall3"), ("mrr", "mrr"), ("context_fact_recall", "context_fact_recall"),
                      ("security_pass_rate", "security"), ("tool_correctness", "tool_correctness"),
                      ("handoff_correctness", "handoff_correctness"), ("false_handoff_rate", "false_handoff"),
                      ("clarify_correctness", "clarify_correctness"), ("false_clarify_rate", "false_clarify")):
        t[name] = _vn(metrics[key])
    t["context_tokens"] = {"value": metrics["context_tokens"]["mean"], "n": metrics["context_tokens"]["n"]}
    for src, dst in (("cost_p50", "cost_p50"), ("cost_p95", "cost_p95"), ("latency_p50", "latency_p50_ms"), ("latency_p95", "latency_p95_ms")):
        if src in metrics:
            t[dst] = {"value": metrics[src]["value"], "n": metrics[src]["n"]}
    if "calls_per_answer" in metrics:
        t["calls_per_answer"] = {"value": metrics["calls_per_answer"]["value"], "n": metrics["calls_per_answer"]["n"]}
        t["hosted_equivalent_cost_p50"] = {"value": metrics["hosted_equivalent_cost_p50"]["value"], "n": metrics["hosted_equivalent_cost_p50"]["n"]}
        t["hosted_equivalent_cost_p95"] = {"value": metrics["hosted_equivalent_cost_p95"]["value"], "n": metrics["hosted_equivalent_cost_p95"]["n"]}
    for src, dst in (("over_refusal", "over_refusals"), ("must_pass", "must_pass_failures")):
        m = metrics[src]
        t[dst] = {"value": m["num"] if m["den"] else 0, "n": m["den"]}
    t["must_pass_failures"]["failed"] = metrics["must_pass"].get("failed_ids", [])
    return t


def case_row(spec: dict, res: dict, v: dict) -> dict:
    """One cases.jsonl line, flat as the dashboard reads it. `spec`, `result` (without steps) and `verdict` ride along
    so diff and confirm can regrade from the stored outputs; the steps (with their eval blocks) sit at the top."""
    def share(name):
        n, d = v["m"].get(name, [0, 0])
        return (n / d) if d else None
    return {"id": spec["id"], "case_id": spec["id"], "kind": spec["kind"], "family": spec.get("family"),
            "slices": spec.get("slices") or [], "expected_action": v.get("expected_action") or spec.get("expected_action"),
            "must_pass": bool(spec.get("must_pass")), "passed": v.get("passed"), "failure_type": v.get("failure"),
            "recall3": share("recall3"), "recall5": share("recall5"), "rr": share("mrr"),
            "context_fact_recall": share("context_fact_recall"), "context_tokens": v.get("context_tokens"),
            "cost_usd": res.get("cost_usd", 0.0), "latency_ms": res.get("latency_ms"), "tokens_in": res.get("tokens_in", 0),
            "tokens_out": res.get("tokens_out", 0), "tool_ok": (v["tool"]["ok"] if v.get("tool") else None),
            "leak_path": v.get("leak_path"), "calls": res.get("calls", 0),
            "hosted_equivalent_usd": res.get("hosted_equivalent_usd", 0.0),
            "steps": res.get("steps") or [], "spec": spec,
            "result": {k: x for k, x in res.items() if k not in ("steps", "case_id")}, "verdict": v}
