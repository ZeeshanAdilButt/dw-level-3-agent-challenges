"""Run records on disk: ids, immutable creation, loading, listing. Earlier records are never overwritten."""
import hashlib
import json
import re
from pathlib import Path

from . import paths
from .util import read_json, read_jsonl


def create_run_dir(prefix: str, root: Path = None):
    """Create runs/<prefix><NNN>/ atomically (never reuses a directory) and return (run_id, path)."""
    runs = (root or paths.root()) / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    pat = re.compile(rf"^{prefix}(\d+)$")
    n = max([int(m.group(1)) for p in runs.iterdir() if (m := pat.match(p.name))] + [0]) + 1
    while True:
        rid = f"{prefix}{n:03d}"
        try:
            (runs / rid).mkdir()
            return rid, runs / rid
        except FileExistsError:
            n += 1


def run_path(run_id: str) -> Path:
    return paths.runs_dir() / run_id


def load_run(run_id: str) -> dict:
    rec = read_json(run_path(run_id) / "run.json")
    if rec is None:
        raise FileNotFoundError(f"no run record for '{run_id}' (looked in runs/{run_id}/run.json)")
    return rec


def load_results(run_id: str) -> list:
    return read_jsonl(run_path(run_id) / "cases.jsonl")


def _canonical(obj) -> str:
    """JSON text of `obj` as it reads back from disk (default=str, as written), keys sorted: line endings and
    indentation do not change it."""
    plain = json.loads(json.dumps(obj, ensure_ascii=False, default=str))
    return json.dumps(plain, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def record_digest(rec: dict, rows: list) -> dict:
    """{"record", "cases"}: SHA-256 of run.json (without this field) and of the cases.jsonl rows. Written when a
    record is finished; `validate`, `regrade` and `keep` refuse a record that no longer matches it."""
    body = {k: v for k, v in rec.items() if k != "digest"}
    return {"record": hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest(),
            "cases": hashlib.sha256(_canonical(rows).encode("utf-8")).hexdigest()}


def digest_problems(run_id: str, rec: dict = None) -> list:
    """What changed in runs/<id>/ since the record was finished. A record written before digests existed has none
    and is not checked."""
    rec = rec if rec is not None else load_run(run_id)
    want = rec.get("digest") if isinstance(rec, dict) else None
    if not isinstance(want, dict):
        return []
    got = record_digest(rec, load_results(run_id))
    out = []
    if want.get("record") != got["record"]:
        out.append(f"{run_id}: run.json was edited after the run (it no longer matches its digest)")
    if want.get("cases") != got["cases"]:
        out.append(f"{run_id}: cases.jsonl was edited after the run (it no longer matches the digest in run.json)")
    return out


def all_runs() -> list:
    runs = paths.runs_dir()
    out = []
    if runs.exists():
        for p in sorted(runs.iterdir()):
            rec = read_json(p / "run.json") if p.is_dir() else None
            if rec and rec.get("run_id"):
                out.append(rec)
    return out


def kept() -> dict:
    """runs/kept.json holds only {"run_id": ...} (the dashboard reads it); the history that revert needs and the
    keep and revert decisions the gate reads live in runs/kept-history.json."""
    base = read_json(paths.runs_dir() / "kept.json", {}) or {}
    hist = read_json(paths.runs_dir() / "kept-history.json", {}) or {}
    return {**hist, **({"run_id": base["run_id"], "kept": base["run_id"]} if base.get("run_id") else {})}
