"""python -m harness validate: check the schema of every run record (and confirm artifact) under runs/."""
import argparse
import sys

from . import paths
from .schema import validate_confirm, validate_run_dir
from .util import read_json


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harness validate")
    ap.add_argument("runs", nargs="*", help="run ids (default: every record under runs/)")
    a = ap.parse_args(argv)
    runs = paths.runs_dir()
    ids = a.runs or sorted(p.name for p in runs.iterdir() if p.is_dir() and (p / "run.json").exists()) if runs.exists() else []
    errs = []
    for rid in ids:
        errs += validate_run_dir(rid)
    confirms = sorted(runs.glob("confirm-*.json")) if runs.exists() and not a.runs else []
    for c in confirms:
        errs += [f"{c.name}: {e}" for e in validate_confirm(read_json(c, {}) or {})]
    kept = read_json(runs / "kept.json") if runs.exists() else None
    if kept is not None and (set(kept) != {"run_id"} or not kept["run_id"]):
        errs.append('kept.json must be exactly {"run_id": "<run>"}')
    elif kept and not (runs / kept["run_id"] / "run.json").exists():
        errs.append(f"kept.json names {kept['run_id']}, which has no run record")
    if errs:
        print("invalid:")
        for e in errs:
            print("  " + e)
        return 1
    print(f"valid: {len(ids)} run record(s), {len(confirms)} confirmation artifact(s)" if (ids or confirms)
          else "nothing to validate: runs/ has no records yet")
    return 0
