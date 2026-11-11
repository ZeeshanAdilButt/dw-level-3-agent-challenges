"""python -m harness keep <run>, python -m harness revert and python -m harness revert <run>.

Bare `revert` goes back to the previous kept run. `revert <run>` turns down the named run: a candidate that was
never kept is recorded as reverted and the kept run stays; a kept run is dropped together with every run kept after
it, and the run kept before it is current again.

runs/kept.json and config/settings.toml change together: both files are written to temporary names first and
moved into place only after both are ready, so one cannot be updated without the other.
"""
import argparse
import json
import os
import re
import sys

from . import config, paths
from .diff import is_partial, selection
from .records import digest_problems, kept as read_kept, load_run
from .util import now_iso


def toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, list):
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    return json.dumps(str(v), ensure_ascii=False)


def render_settings_toml(existing: str, settings: dict) -> str:
    """Update `key = value` lines in place (sections are kept); keys not in the file go before the first table."""
    lines = existing.splitlines()
    seen = set()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)([A-Za-z_]\w*)\s*=", line)
        if m and m.group(2) in config.DEFAULTS and m.group(2) in settings:
            lines[i] = f"{m.group(1)}{m.group(2)} = {toml_value(settings[m.group(2)])}"
            seen.add(m.group(2))
    missing = [k for k in config.DEFAULTS if k in settings and k not in seen]
    if missing:
        add = [f"{k} = {toml_value(settings[k])}" for k in missing]
        first_table = next((i for i, l in enumerate(lines) if l.lstrip().startswith("[")), len(lines))
        lines[first_table:first_table] = add + ([""] if first_table < len(lines) else [])
    return "\n".join(lines).rstrip("\n") + "\n"


def write_together(kept_run: str, extra: dict, settings: dict) -> None:
    """kept.json ({"run_id"} only), kept-history.json and settings.toml: all temporary first, then moved into place."""
    runs = paths.runs_dir()
    toml_path = paths.root() / "config" / "settings.toml"
    runs.mkdir(parents=True, exist_ok=True)
    toml_path.parent.mkdir(parents=True, exist_ok=True)
    existing = toml_path.read_text(encoding="utf-8") if toml_path.exists() else "# settings of the last kept run" + chr(10)
    files = {runs / "kept.json": json.dumps({"run_id": kept_run}, indent=1) + chr(10),
             runs / "kept-history.json": json.dumps(extra, indent=1) + chr(10),
             toml_path: render_settings_toml(existing, settings)}
    tmps = {}
    for path, text in files.items():
        tmps[path] = path.with_name(path.name + ".tmp")
        tmps[path].write_text(text, encoding="utf-8")
    for path, tmp in tmps.items():
        os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harness keep")
    ap.add_argument("run")
    a = ap.parse_args(argv)
    try:
        rec = load_run(a.run)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if rec.get("kind") != "run" or rec.get("status") != "complete":
        print(f"error: {a.run} is not a complete full run (a screen or an unfinished run cannot be kept)", file=sys.stderr)
        return 2
    bad = digest_problems(a.run, rec)
    if bad:
        print("error: " + "; ".join(bad), file=sys.stderr)
        return 2
    if is_partial(rec):
        print(f"error: {a.run} ran a subset of the cases ({selection(rec)}); only a full run can be kept", file=sys.stderr)
        return 2
    cur = read_kept()
    history = list(cur.get("history") or [])
    if history and history[-1]["run"] == a.run:
        print(f"{a.run} is already the last kept run")
        return 0
    history.append({"run": a.run, "at": now_iso(), "settings": rec["settings"], "parent": rec.get("parent")})
    decisions = list(cur.get("decisions") or []) + [{"run": a.run, "action": "keep", "at": now_iso()}]
    write_together(a.run, {"history": history, "decisions": decisions, "updated_at": now_iso()}, rec["settings"])
    print(f"kept {a.run}; runs/kept.json and config/settings.toml now hold its settings. Commit both before the next run.")
    return 0


def revert_named(run_id: str, cur: dict) -> int:
    try:
        rec = load_run(run_id)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    history = list(cur.get("history") or [])
    names = [h["run"] for h in history]
    decisions = list(cur.get("decisions") or [])
    if run_id not in names:
        if any(d["run"] == run_id and d["action"] == "revert" for d in decisions):
            print(f"{run_id} is already reverted")
            return 0
        if rec.get("kind") != "run":
            print(f"error: {run_id} is not a run (a screen is not kept or reverted)", file=sys.stderr)
            return 2
        decisions.append({"run": run_id, "action": "revert", "at": now_iso()})
        path = paths.runs_dir() / "kept-history.json"       # only the decision record changes; kept.json and settings stay
        paths.runs_dir().mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        extra = {"history": history, "decisions": decisions, "updated_at": now_iso()}
        if cur.get("reverted"):
            extra["reverted"] = cur["reverted"]
        tmp.write_text(json.dumps(extra, indent=1) + chr(10), encoding="utf-8")
        os.replace(tmp, path)
        print(f"{run_id} was never kept and is now recorded as reverted; the last kept run is "
              f"{names[-1] if names else 'still none'}. Commit runs/kept-history.json.")
        return 0
    at = names.index(run_id)
    if at == 0:
        print(f"error: {run_id} is the first kept run; there is nothing before it to go back to", file=sys.stderr)
        return 2
    dropped = history[at:]
    history = history[:at]
    prev = history[-1]
    decisions += [{"run": h["run"], "action": "revert", "at": now_iso()} for h in dropped]
    write_together(prev["run"], {"history": history, "decisions": decisions, "updated_at": now_iso(),
                                 "reverted": run_id}, prev["settings"])
    print(f"reverted {', '.join(h['run'] for h in dropped)}; the last kept run is {prev['run']} again. "
          "Commit runs/kept.json and config/settings.toml.")
    return 0


def main_revert(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harness revert")
    ap.add_argument("run", nargs="?", help="a run to turn down (default: the last kept run)")
    a = ap.parse_args(argv)
    cur = read_kept()
    if a.run:
        return revert_named(a.run, cur)
    history = list(cur.get("history") or [])
    if len(history) < 2:
        print("error: nothing to revert to (there is no earlier kept run)", file=sys.stderr)
        return 2
    dropped = history.pop()
    prev = history[-1]
    decisions = list(cur.get("decisions") or []) + [{"run": dropped["run"], "action": "revert", "at": now_iso()}]
    write_together(prev["run"], {"history": history, "decisions": decisions, "updated_at": now_iso(),
                                 "reverted": dropped["run"]}, prev["settings"])
    print(f"reverted {dropped['run']}; the last kept run is {prev['run']} again. Commit runs/kept.json and config/settings.toml.")
    return 0
