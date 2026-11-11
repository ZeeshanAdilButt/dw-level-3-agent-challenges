"""Checks that this machine can run the course, and says which model path to use.

    python tools/doctor.py [--skip-model] [--calls 5] [--out doctor.json]

Checks: Python version, SQLite FTS5 with bm25(), Git, Ollama reachable with the two models present, disk space.
Then it times five real chat calls and compares the median with 8 seconds: at or under, use the local path;
over, use the hosted path. Standard library only. Exit code 1 if a required check fails.
The result is also written to doctor.json (the receipt a learner commits).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
MEDIAN_LIMIT_S = 8.0
MIN_PYTHON = (3, 11)
MIN_FREE_GB = 10.0
LOCAL_MODELS = ("qwen3:4b-instruct", "nomic-embed-text")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")

# A prompt shaped like a real agent call: rules, five short chunks and a question.
SYSTEM = ("You are a customer assistant. Answer only from the context. Cite the document id in square brackets. "
          "If the context does not contain the answer, say you do not know.")
CONTEXT = "\n\n".join(f"[doc-sample-{i}] " + ("Plans are billed per seat per month. Annual billing is cheaper. " * 6)
                      for i in range(5))
QUESTION = "How much is the Pro plan per seat if we pay every month?"


class Result:
    def __init__(self, name: str, ok: bool, detail: str, required: bool = True):
        self.name, self.ok, self.detail, self.required = name, ok, detail, required

    def line(self) -> str:
        mark = "ok  " if self.ok else ("FAIL" if self.required else "warn")
        return f"[{mark}] {self.name}: {self.detail}"


def check_python() -> Result:
    v = sys.version_info
    ok = (v.major, v.minor) >= MIN_PYTHON
    return Result("Python", ok, f"{v.major}.{v.minor}.{v.micro}" + ("" if ok else f" (need {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer)"))


def check_fts5() -> Result:
    try:
        con = sqlite3.connect(":memory:")
        con.execute("CREATE VIRTUAL TABLE t USING fts5(body)")
        con.execute("INSERT INTO t(body) VALUES ('annual billing is cheaper'), ('monthly billing')")
        row = con.execute("SELECT body, bm25(t) FROM t WHERE t MATCH 'annual' ORDER BY bm25(t)").fetchone()
        con.close()
        return Result("SQLite FTS5 and bm25()", row is not None, f"SQLite {sqlite3.sqlite_version}, bm25 score {row[1]:.3f}" if row else "no row")
    except sqlite3.Error as exc:
        return Result("SQLite FTS5 and bm25()", False, f"not available ({exc}). Install a Python built with FTS5.")


def check_git() -> Result:
    try:
        out = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=10)
        return Result("Git", out.returncode == 0, out.stdout.strip() or out.stderr.strip())
    except (OSError, subprocess.SubprocessError) as exc:
        return Result("Git", False, f"not found ({exc})")


def check_disk(path: str = ".") -> Result:
    free_gb = shutil.disk_usage(path).free / 1e9
    return Result("Disk space", free_gb >= MIN_FREE_GB, f"{free_gb:.1f} GB free here (models and runs need about {MIN_FREE_GB:.0f} GB)",
                  required=False)


def _get_json(url: str, body: dict | None = None, timeout: float = 120.0) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def installed_models() -> list[str]:
    tags = _get_json(OLLAMA_URL + "/api/tags", timeout=5.0)
    return [m.get("name", "") for m in tags.get("models", [])]


def model_present(wanted: str, names: list[str]) -> bool:
    """Ollama lists `nomic-embed-text` as `nomic-embed-text:latest`; a tagged name must match exactly."""
    return any(n == wanted or (":" not in wanted and n == wanted + ":latest") for n in names)


def check_ollama() -> tuple[Result, Result | None]:
    try:
        names = installed_models()
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return Result("Ollama", False, f"not reachable at {OLLAMA_URL} ({exc}). Start it with `ollama serve`.", required=False), None
    missing = [m for m in LOCAL_MODELS if not model_present(m, names)]
    models = Result("Models", not missing, "both present" if not missing
                    else "missing " + ", ".join(missing) + ". Run: " + "; ".join(f"ollama pull {m}" for m in missing), required=False)
    return Result("Ollama", True, f"reachable at {OLLAMA_URL}"), models


def time_calls(calls: int = 5, model: str = LOCAL_MODELS[0]) -> list[float]:
    """Seconds for each of `calls` chat calls, one at a time. The first call includes loading the model."""
    times = []
    for _ in range(calls):
        body = {"model": model, "temperature": 0.2, "max_tokens": 80,
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": f"Context:\n{CONTEXT}\n\nQuestion: {QUESTION}"}]}
        start = time.perf_counter()
        _get_json(OLLAMA_URL + "/v1/chat/completions", body)
        times.append(time.perf_counter() - start)
    return times


def choose_path(times: list[float], limit: float = MEDIAN_LIMIT_S) -> tuple[str, float]:
    """`local` when the median call is at or under the limit, else `hosted`. No timings means `hosted`."""
    if not times:
        return "hosted", float("nan")
    med = statistics.median(times)
    return ("local" if med <= limit else "hosted"), med


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-model", action="store_true", help="do not time model calls (CI, or no Ollama)")
    ap.add_argument("--calls", type=int, default=5)
    ap.add_argument("--out", default=str(HERE / "doctor.json"), help="where to write the receipt (default: doctor.json at the repository root)")
    args = ap.parse_args(argv)

    results = [check_python(), check_fts5(), check_git(), check_disk()]
    ollama, models = check_ollama()
    results.append(ollama)
    if models:
        results.append(models)
    for r in results:
        print(r.line())

    path_msg = ""
    times, chosen, median = [], None, None
    if args.skip_model:
        path_msg = "Model timing skipped."
    elif not (ollama.ok and models and models.ok):
        path_msg = ("Use the hosted path: the local model is not ready. Fix the lines above, or set model_path = \"hosted\" "
                    "in config/settings.toml.")
    else:
        print(f"Timing {args.calls} chat calls on {LOCAL_MODELS[0]} (the first one loads the model) ...")
        try:
            times = time_calls(args.calls)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            times = []
            print(f"[FAIL] chat call failed: {exc}")
        print("Seconds per call: " + ", ".join(f"{t:.1f}" for t in times))
        path, med = choose_path(times)
        chosen, median = path, (med if times else None)
        if times:
            path_msg = (f"Median {med:.1f} s against the {MEDIAN_LIMIT_S:.0f} s limit. Use the {path.upper()} path"
                        + (" (model_path = \"local\")." if path == "local" else
                           ": this machine is too slow for the local model. Set model_path = \"hosted\" in config/settings.toml."))
        else:
            path_msg = "Use the hosted path: the local calls failed."
    if path_msg:
        print(path_msg)
    failed = [r for r in results if r.required and not r.ok]
    receipt = {"written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "python": sys.version.split()[0],
               "checks": [{"name": r.name, "ok": r.ok, "required": r.required, "detail": r.detail} for r in results],
               "model_timing": {"skipped": bool(args.skip_model), "seconds_per_call": [round(t, 2) for t in times],
                                "median_s": None if median is None else round(median, 2), "limit_s": MEDIAN_LIMIT_S},
               "model_path": chosen or ("hosted" if not args.skip_model else None), "required_checks_passed": not failed}
    try:
        Path(args.out).write_text(json.dumps(receipt, indent=1) + chr(10), encoding="utf-8")
        print(f"Wrote {Path(args.out).name}.")
    except OSError as exc:
        print(f"Could not write {args.out}: {exc}")
    if failed:
        print(f"{len(failed)} required check(s) failed.")
        return 1
    print("Required checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
