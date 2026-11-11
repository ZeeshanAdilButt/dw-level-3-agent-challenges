"""Where things live. The root can be moved with DW_ROOT (tests, snapshots)."""
import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def root() -> Path:
    return Path(os.environ.get("DW_ROOT") or PACKAGE_ROOT)


def runs_dir() -> Path:
    return root() / "runs"


def pack_dir(pack: str) -> Path:
    return root() / "packs" / pack
