"""Lab 1, part 1: setup and the doctor.

Invariant (passes on the starter): test_settings_parse, test_doctor_rule, test_model_names.
Acceptance (fails on the starter): test_doctor_receipt, with
    AssertionError: results.md has no doctor receipt
"""
import importlib.util
import re
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "challenges" / "_shared"))

from panel_render import is_reference_tree  # noqa: E402

PACKS = ("quillon", "juniper", "saltmarsh")
PATHS = ("local", "hosted")


def load_doctor():
    spec = importlib.util.spec_from_file_location("dw_doctor", ROOT / "tools" / "doctor.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_receipt(text: str, settings: dict, gitignore: str) -> list:
    """The problems with a results.md receipt. An empty list means it holds a receipt."""
    problems = []
    if not text.strip() or text.lstrip().startswith("# Results\n\nRun this part"):
        return ["results.md has no doctor receipt"]
    for name in ("Python", "SQLite FTS5 and bm25()", "Git"):
        if not re.search(r"^\[ok  \] " + re.escape(name) + r":", text, re.M):
            problems.append(f"no passing '{name}' check line (the lines start with [ok  ])")
    median = re.search(r"Median (\d+(?:\.\d+)?) s against the 8 s limit", text)
    if not median and "Use the hosted path" not in text:
        problems.append("no median call time and no hosted-path line from the doctor")
    pack = re.search(r"^company:\s*(\w+)\s*$", text, re.M | re.I)
    path = re.search(r"^model path:\s*(\w+)\s*$", text, re.M | re.I)
    if not pack or pack.group(1) not in PACKS:
        problems.append("the line 'company: <quillon, juniper or saltmarsh>' is missing")
    elif pack.group(1) != settings["pack"]:
        problems.append(f"results.md says company {pack.group(1)} but config/settings.toml says {settings['pack']}")
    if not path or path.group(1) not in PATHS:
        problems.append("the line 'model path: <local or hosted>' is missing")
    elif path.group(1) != settings["model_path"]:
        problems.append(f"results.md says model path {path.group(1)} but config/settings.toml says {settings['model_path']}")
    if median and path and path.group(1) == "local" and float(median.group(1)) > 8:
        problems.append("a median over 8 seconds picks the hosted path, not local")
    if median and path and path.group(1) == "hosted" and float(median.group(1)) <= 8:
        problems.append("a median of 8 seconds or less picks the local path, not hosted")
    if ".env" not in [ln.strip() for ln in gitignore.splitlines()]:
        problems.append(".gitignore has no .env line")
    return problems


GOOD = """# Results

[ok  ] Python: 3.12.1
[ok  ] SQLite FTS5 and bm25(): SQLite 3.45.1, bm25 score -0.000
[ok  ] Git: git version 2.43.0
[ok  ] Ollama: reachable at http://localhost:11434
Seconds per call: 9.1, 4.2, 4.0, 4.1, 4.3
Median 4.2 s against the 8 s limit. Use the LOCAL path (model_path = "local").
company: juniper
model path: local
"""


# ---- invariant ---------------------------------------------------------------------------------------------------

def test_settings_parse():
    raw = tomllib.loads((ROOT / "config" / "settings.toml").read_text(encoding="utf-8"))
    assert "lab1" in raw
    from app.settings import load_settings
    s = load_settings()
    assert s["pack"] in PACKS and s["model_path"] in ("local", "hosted", "stub")


def test_doctor_rule():
    doctor = load_doctor()
    assert doctor.choose_path([6.0] * 5)[0] == "local"          # inside the rule, with or without a GPU
    assert doctor.choose_path([8.0] * 5)[0] == "local"          # the limit itself is still local
    assert doctor.choose_path([8.1, 9.0, 7.0, 9.5, 8.4])[0] == "hosted"
    assert doctor.choose_path([])[0] == "hosted"                # no timings means hosted


def test_model_names():
    doctor = load_doctor()
    assert doctor.LOCAL_MODELS == ("qwen3:4b-instruct", "nomic-embed-text")
    assert doctor.model_present("nomic-embed-text", ["nomic-embed-text:latest"])
    assert not doctor.model_present("qwen3:4b-instruct", ["qwen3:4b"])


def test_the_receipt_checker_on_fixed_receipts():
    s = {"pack": "juniper", "model_path": "local"}
    assert check_receipt(GOOD, s, ".env\n__pycache__/\n") == []
    assert check_receipt(GOOD, {"pack": "quillon", "model_path": "local"}, ".env\n")          # wrong company
    assert check_receipt(GOOD.replace("Median 4.2 s", "Median 4.2 seconds"), s, ".env\n")     # no median line
    assert check_receipt(GOOD, s, "__pycache__/\n")                                            # .env not ignored
    assert check_receipt(GOOD.replace("[ok  ] Git", "[FAIL] Git"), s, ".env\n")               # a failed check
    assert check_receipt("# Results\n\nRun this part to write this file.\n", s, ".env\n") == ["results.md has no doctor receipt"]


# ---- acceptance --------------------------------------------------------------------------------------------------

@pytest.mark.skipif(is_reference_tree(), reason="the reference tree holds no learner receipt; the checker is tested above")
def test_doctor_receipt():
    results = (HERE / "results.md").read_text(encoding="utf-8") if (HERE / "results.md").exists() else ""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
    from app.settings import load_settings
    problems = check_receipt(results, load_settings(), gitignore)
    assert not problems, "; ".join(problems)
