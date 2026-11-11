"""Small shared helpers: JSON, hashing, git, percentiles."""
import hashlib
import json
import math
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import paths


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha(data) -> str:
    if not isinstance(data, (bytes, bytearray)):
        data = (data if isinstance(data, str) else json.dumps(data, sort_keys=True, default=str)).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def read_jsonl(path) -> list:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path, rows) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in rows), encoding="utf-8")


def git(*args, cwd=None):
    """Run git, return stdout stripped, or None when git fails or is missing."""
    try:
        out = subprocess.run(["git", *args], cwd=str(cwd or paths.root()), capture_output=True, text=True,
                             encoding="utf-8", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def percentile(values, p):
    """Nearest rank: the value at rank ceil(p/100 * n). None for an empty list."""
    if not values:
        return None
    s = sorted(values)
    return s[max(1, math.ceil(p / 100 * len(s))) - 1]


def pct(x, digits=0):
    return "-" if x is None else f"{100 * x:.{digits}f}%"
