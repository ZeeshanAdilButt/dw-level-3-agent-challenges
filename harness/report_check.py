"""python -m harness report-check [REPORT.md]: every linked measured number must match its artifact, and the page
must fit in 600 words (decision E6).

A measured number is a link like [64% answer success](runs/confirm-r031.json#best.answer_success). The file is
read relative to the repository root, the path after # is walked through the JSON (dotted keys), and the number in
the link text must equal the stored value (a percentage to the rounding shown, a count exactly). Configuration
values and design counts are not links and are not checked.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from . import paths

LINK = re.compile(r"\[([^\]]+)\]\(([^)#\s]+)#([^)\s]+)\)")
ANY_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?%?")
MAX_WORDS = 600


def walk(obj, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            raise KeyError(part)
    return cur


def leaf_value(x):
    if isinstance(x, dict) and "value" in x:
        return x["value"]
    return x


# Numbers that are part of a metric's name, not its measured value: recall5, p50, p95, l9, "recall at 5", "top 3", "@5".
NAME_NUMBERS = [re.compile(r"\b[A-Za-z_]+\d+\w*"), re.compile(r"\b(?:at|top)\s+\d+\b", re.IGNORECASE), re.compile(r"@\s*\d+")]


def measured_number(text: str):
    """The first number in a link's text once the numbers of metric names are taken out:
    "[recall at 5: 72.0%]" gives 72.0%, "[p50 latency 310 ms]" gives 310."""
    for pat in NAME_NUMBERS:
        text = pat.sub(" ", text)
    return NUMBER.search(text)


def numbers_match(text: str, value) -> bool:
    m = measured_number(text)
    if not m or value is None or isinstance(value, (str, bool, list, dict)):
        return False
    tok = m.group(0)
    if float(tok.rstrip("%")) == 0 and value != 0:          # "0" or "0%" for a value that rounds down to it is not zero
        return False
    if tok.endswith("%"):
        shown = float(tok[:-1])
        decimals = len(tok[:-1].split(".")[1]) if "." in tok else 0
        return abs(round(100 * value, decimals) - shown) < 1e-9
    shown = float(tok)
    decimals = len(tok.split(".")[1]) if "." in tok else 0
    return abs(round(value, decimals) - shown) < 1e-9


def word_count(md: str) -> int:
    text = re.sub(r"<!--.*?-->", " ", md, flags=re.S)
    text = re.sub(r"^---\n.*?\n---\n", " ", text, flags=re.S)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = ANY_LINK.sub(lambda m: m.group(1), text)
    return len([w for w in text.split() if re.search(r"\w", w)])


def check_text(md: str, root: Path) -> tuple:
    """Return (problems, n_links, words)."""
    problems = []
    md = re.sub(r"<!--.*?-->", " ", md, flags=re.S)       # a link or number inside an HTML comment is not in the page
    links = LINK.findall(md)
    for text, path, frag in links:
        f = (root / path)
        if not f.exists():
            problems.append(f"'{text}': {path} does not exist")
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            value = leaf_value(walk(data, frag))
        except KeyError as e:
            problems.append(f"'{text}': {path} has no '{frag}' (stopped at {e.args[0]})")
            continue
        except ValueError:
            problems.append(f"'{text}': {path} is not valid JSON")
            continue
        if not numbers_match(text, value):
            problems.append(f"'{text}': {path}#{frag} is {value!r}")
    words = word_count(md)
    if words > MAX_WORDS:
        problems.append(f"the page is {words} words; the limit is {MAX_WORDS}")
    return problems, len(links), words


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harness report-check")
    ap.add_argument("report", nargs="?", default="REPORT.md")
    a = ap.parse_args(argv)
    f = Path(a.report)
    if not f.is_absolute():
        f = paths.root() / f
    if not f.exists():
        print(f"error: {a.report} not found", file=sys.stderr)
        return 2
    problems, n, words = check_text(f.read_text(encoding="utf-8"), paths.root())
    if problems:
        print(f"report-check: {len(problems)} problem(s)")
        for p in problems:
            print("  " + p)
        return 1
    print(f"report-check: {n} linked number(s) match their artifacts; {words} words (limit {MAX_WORDS})")
    return 0
