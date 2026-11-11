"""python -m harness status: the kept run, the last runs and the runs still waiting for a keep or revert decision."""
import argparse

from .diff import is_partial
from .records import all_runs, kept


def pending_decisions(runs: list, k: dict) -> list:
    """Complete full runs with a parent and a change to judge that were neither kept nor reverted. A smoke or slice run
    (which keep refuses) and a rerun with no change (the noise floor) wait for nothing."""
    decided = {d["run"] for d in k.get("decisions") or []} | {h["run"] for h in k.get("history") or []}
    return [r for r in runs if r.get("kind") == "run" and r.get("status") == "complete" and r.get("parent")
            and r.get("change") != {} and not is_partial(r) and r["run_id"] not in decided]


def _line(r: dict) -> str:
    m = (r.get("totals") or {}).get("answer_success") or {}
    shown = "-" if m.get("value") is None else f"{100 * m['value']:.1f}%"
    change = ", ".join(f"{key} {a!r} -> {b!r}" for key, (a, b) in (r.get("change") or {}).items()) or "no change"
    return f"  {r['run_id']:8s} {r.get('kind', ''):7s} {r.get('status', 'complete'):11s} answer success {shown:>6s}  {change}"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harness status")
    ap.add_argument("--last", type=int, default=5, help="how many recent runs to list")
    a = ap.parse_args(argv)
    runs = all_runs()
    k = kept()
    print("kept run: " + (k.get("run_id") or "none yet (run `harness keep <run>` on your baseline)"))
    shown = [r for r in runs if r.get("kind") in ("run", "screen")][-a.last:]
    print(f"last {len(shown)} run(s):")
    for r in shown:
        print(_line(r))
    if not shown:
        print("  none yet")
    pend = pending_decisions(runs, k)
    print("pending decisions: " + (", ".join(r["run_id"] for r in pend) if pend else "none"))
    for r in pend:
        print(f"  {r['run_id']}: `harness keep {r['run_id']}` or `harness revert {r['run_id']}`")
    return 0
