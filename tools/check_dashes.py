"""Fails when a file holds an em dash or an en dash.

    python tools/check_dashes.py FILE_OR_FOLDER [...]   exit 1 and list each place; exit 0 when clean
    python tools/check_dashes.py --warn FILE ...         list the places but always exit 0 (a warning only)

A folder is searched for text files (md, py, js, css, html, json, jsonl, yaml, yml, toml, txt). A plain hyphen or a
range such as 60-70 is fine. Standard library only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

DASHES = {"\u2014": "em dash", "\u2013": "en dash"}
SUFFIXES = {".md", ".py", ".js", ".css", ".html", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".txt"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".cache", "runs"}


def files_of(targets: list[str]) -> list[Path]:
    out = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            out += sorted(f for f in p.rglob("*") if f.is_file() and f.suffix in SUFFIXES and not (SKIP_DIRS & set(f.parts)))
        elif p.is_file():
            out.append(p)
    return out


def find_dashes(path: Path) -> list[tuple[int, str]]:
    """[(line number, dash name)] for every long dash in the file."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    return [(n, name) for n, line in enumerate(text.splitlines(), 1) for ch, name in DASHES.items() if ch in line]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--warn", action="store_true", help="print the places but never fail")
    args = ap.parse_args(argv)
    found = 0
    for f in files_of(args.paths):
        for n, name in find_dashes(f):
            found += 1
            print(f"{f}:{n}: {name}")
    if not found:
        print("no em or en dashes")
        return 0
    print(f"{found} long dash(es) found" + (" (warning only)" if args.warn else ""))
    return 0 if args.warn else 1


if __name__ == "__main__":
    raise SystemExit(main())
