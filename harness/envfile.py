"""A tiny .env loader (no dependency). Lines are KEY=VALUE; blank lines and lines starting with # are skipped; one
pair of quotes around a value is removed. A variable that is already set in the environment is never overwritten, so
a real environment variable always wins over the file. The file is never printed."""
import os
from pathlib import Path

from . import paths


def parse(text: str) -> dict:
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            out[key] = value
    return out


def load_env(path=None) -> list:
    """Fill environment variables that are not set from .env. Returns the names that were filled."""
    f = Path(path) if path else paths.root() / ".env"
    if not f.is_file():
        return []
    filled = []
    for key, value in parse(f.read_text(encoding="utf-8")).items():
        if key not in os.environ:
            os.environ[key] = value
            filled.append(key)
    return filled
