"""python -m harness screen: retrieval only, no chat model.

Exact and fast, so it reports changes, not verdicts. Every execution writes a new immutable record under
runs/s<NNN>/ with its start time, the prediction commit (the last commit that touched predictions/), code and
corpus fingerprints and the embedding model. An earlier record is never overwritten, so the order of "predict"
and "screen" can be read from the records (process evidence, not proof against deliberate gaming).
"""
import argparse
import sys
import time
from collections import defaultdict

from . import config, paths
from .cases import load_cases, load_context
from .fingerprint import build_manifest, prediction_commit
from .graders import GRADER_VERSION, grade_case
from .graders.recall import reciprocal_rank
from .records import all_runs, create_run_dir, record_digest
from .retrieval_bridge import RetrievalBridge, install_embedding_stats
from .util import now_iso, write_json, write_jsonl

OTHER_KEYS = ("pack", "chunker", "chunk_size", "overlap", "top_k", "embed_model", "context", "neighbours_n",
              "context_token_limit", "authority_rule")


def add_arguments(ap):
    ap.add_argument("--pack", required=True)
    ap.add_argument("--set", action="append", default=[], metavar="key=value")
    ap.add_argument("--parent", help="a run whose resolved settings are the starting point (default: the last kept run)")
    ap.add_argument("--label", default="")
    # legacy flags of `python -m harness.screen`
    ap.add_argument("--chunker")
    ap.add_argument("--size", type=int)
    ap.add_argument("--overlap", type=int)
    ap.add_argument("--retriever")


def _agg(rows):
    def mean(key):
        return round(sum(r[key] for r in rows) / len(rows), 3)
    found = sum(r["facts_found"] for r in rows)
    total = sum(r["facts_total"] for r in rows)
    cov = sum(r["spans_covered"] for r in rows)
    ctot = sum(r["spans_total"] for r in rows)
    forms = [r["forms_recall"] for r in rows if r["forms_recall"] is not None]
    return {"n": len(rows), "recall3": mean("recall3"), "recall5": mean("recall5"), "mrr": mean("rr"), "mrr_doc": mean("rr_doc"),
            "span_coverage": round(cov / ctot, 3) if ctot else None, "spans": ctot,
            "context_fact_recall": round(found / total, 3) if total else None, "facts": total,
            "forms_recall": round(sum(forms) / len(forms), 3) if forms else None,
            "context_tokens": round(sum(r["context_tokens"] for r in rows) / len(rows))}


def summarise(rows):
    by = defaultdict(list)
    for r in rows:
        for s in r["slices"]:
            by[s].append(r)
    return _agg(rows), {s: _agg(v) for s, v in sorted(by.items())}


def _same_other_settings(a: dict, b: dict) -> bool:
    return all(a.get(k) == b.get(k) for k in OTHER_KEYS)


def latest_bm25_baseline(settings: dict, exclude: str = None):
    best = None
    for rec in all_runs():
        if rec.get("kind") != "screen" or rec["run_id"] == exclude:
            continue
        s = rec.get("settings") or {}
        if s.get("retriever") == "bm25" and _same_other_settings(s, settings):
            if best is None or rec.get("started_at", "") > best.get("started_at", ""):
                best = rec
    return best


def wins_ties_losses(rows, base_rows):
    base = {r["id"]: r for r in base_rows}

    def wtl(sel):
        w = t = l = 0
        for r in sel:
            if r["id"] not in base:
                continue
            d = r["recall5"] - base[r["id"]]["recall5"]
            w, l, t = w + (d > 0), l + (d < 0), t + (d == 0)
        return f"{w}-{t}-{l}"
    out = {"all": wtl(rows)}
    for s in sorted({s for r in rows for s in r["slices"]}):
        out[s] = wtl([r for r in rows if s in r["slices"]])
    return out


def screen_cases(settings: dict, bridge: RetrievalBridge, cases: list, ctx: dict) -> list:
    from app.types import principal_from_dict
    rows = []
    for spec in cases:
        if spec["kind"] != "question" or "retrieval" not in (spec.get("needs") or []) or not spec.get("gold_sources"):
            continue
        step = spec["steps"][-1]
        r = bridge.retrieve(step["text"], principal_from_dict(step["principal"]))
        ids = list(dict.fromkeys(r.ranked_ids + r.expanded_ids + r.delivered_ids))
        stored = {"steps": [{"step_id": step["id"], "reply": {}, "offsets": {i: bridge.table[i] for i in ids if i in bridge.table},
                             "eval": {"ranked_hit_ids": r.ranked_ids, "expanded_evidence_ids": r.expanded_ids,
                                      "delivered_evidence_ids": r.delivered_ids, "delivered_text": r.delivered_text,
                                      "delivered_tokens": r.delivered_tokens, "truncated": r.truncated}}]}
        v = grade_case(spec, stored, ctx, mode="retrieval_only")
        m = v["m"]
        kf = spec.get("key_facts") or []
        low = r.delivered_text.lower()
        forms = (sum(any(str(f).lower() in low for f in k["forms"]) for k in kf) / len(kf)) if kf else None
        rows.append({
            "id": spec["id"], "kind": "question", "slices": spec["slices"], "expected_action": spec.get("expected_action"),
            "must_pass": bool(spec.get("must_pass")), "passed": None, "failure_type": None,
            "context_fact_recall": (m["context_fact_recall"][0] / m["context_fact_recall"][1]) if m["context_fact_recall"][1] else None, "retrieved": r.ranked_ids, "expanded": r.expanded_ids,
            "delivered": r.delivered_ids, "truncated": r.truncated,
            "recall3": m["recall3"][0], "recall5": m["recall5"][0], "rr": m["mrr"][0],
            "rr_doc": reciprocal_rank(r.ranked_ids, spec["gold_sources"], [], {}),
            "spans_covered": m["span_coverage"][0], "spans_total": m["span_coverage"][1],
            "facts_found": m["context_fact_recall"][0], "facts_total": m["context_fact_recall"][1],
            "fact_recall": (m["context_fact_recall"][0] / m["context_fact_recall"][1]) if m["context_fact_recall"][1] else None,
            "forms_recall": forms, "context_tokens": r.delivered_tokens})
    return rows


def run_screen(args) -> int:
    started = now_iso()
    t0 = time.time()
    sets = config.parse_sets(args.set)
    for flag, key in (("chunker", "chunker"), ("size", "chunk_size"), ("overlap", "overlap"), ("retriever", "retriever")):
        if getattr(args, flag, None) is not None:
            sets[key] = getattr(args, flag)
    settings, parent, change = config.resolve(pack=args.pack, parent=args.parent, sets=sets)
    print(config.describe(settings, change))
    pd = paths.pack_dir(settings["pack"])
    if not pd.exists():
        print(f"error: no pack folder {pd}", file=sys.stderr)
        return 2
    pred = prediction_commit()
    cases = load_cases(settings["pack"])
    ctx = load_context(pd)
    needs_embeddings = settings["retriever"] in ("vector", "hybrid")
    stats = install_embedding_stats(settings["embed_model"], uncached_queries=False) if needs_embeddings else None
    bridge = RetrievalBridge(settings, pd)
    index_stats = dict(stats) if stats else None
    if stats:
        for k in ("lookups", "cache_misses", "network_calls"):
            stats[k] = 0
    rows = screen_cases(settings, bridge, cases, ctx)
    overall, slices = summarise(rows)
    base = latest_bm25_baseline(settings)
    wtl = base_id = None
    if base is not None and settings["retriever"] != "bm25":
        from .records import load_results
        wtl, base_id = wins_ties_losses(rows, load_results(base["run_id"])), base["run_id"]
    rid, out = create_run_dir("s")
    manifest = build_manifest(settings, pd, embed_digest=needs_embeddings, model_digest=False)
    cfg = {k: settings[k] for k in ("pack", "chunker", "chunk_size", "overlap", "retriever", "top_k")}
    record = {
        "run_id": rid, "kind": "screen", "label": args.label, "started_at": started, "ended_at": now_iso(),
        "parent": parent, "change": change, "explicit_sets": sorted(sets), "settings": settings, "manifest": manifest,
        "prediction_commit": pred["commit"], "prediction_committed_at": pred["committed_at"],
        "grader_version": GRADER_VERSION, "retrieval_path": bridge.path, "chunks": len(bridge.chunks),
        "embedding": ({"index": index_stats, "queries": stats} if stats else None),
        "fingerprint": manifest["fingerprint"], "config": cfg, "overall": overall, "slices": slices, "baseline_bm25": base_id, "wins_ties_losses": wtl,
        "seconds": round(time.time() - t0, 1)}
    record["digest"] = record_digest(record, rows)
    write_json(out / "run.json", record)
    write_jsonl(out / "cases.jsonl", rows)
    cfg = {k: settings[k] for k in ("pack", "chunker", "chunk_size", "overlap", "retriever", "top_k")}
    print(f"\n{rid} screen {cfg} {len(bridge.chunks)} chunks, retrieval via {bridge.path}")
    if pred["commit"] is None:
        print("note: no prediction commit found (nothing committed under predictions/ yet)")
    print("overall", overall)
    for s, v in slices.items():
        print(f"  {s:18s}", v)
    if wtl:
        print(f"against the latest BM25 screen {base_id} (same other settings), wins-ties-losses on recall at 5:")
        for k, v in wtl.items():
            print(f"  {k:18s} {v}")
    elif settings["retriever"] != "bm25":
        print("no earlier BM25 screen with the same other settings: run `screen --set retriever=bm25` first for wins, ties and losses")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harness screen")
    add_arguments(ap)
    return run_screen(ap.parse_args(argv))
