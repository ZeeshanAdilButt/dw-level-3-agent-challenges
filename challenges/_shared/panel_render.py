"""Run one dashboard panel in Node with a fake DOM and return what it drew (see panel_render.js)."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def render_panel(panel_file: str, ctx: dict) -> dict:
    """panel_file is a name under dashboard/panels/, for example "diff.js". ctx holds run, base, cases, baseCases, runs, kept."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the dashboard panels need it to be tested")
    with tempfile.TemporaryDirectory() as tmp:
        ctx_file = Path(tmp) / "ctx.json"
        ctx_file.write_text(json.dumps(ctx), encoding="utf-8")
        out = subprocess.run([node, str(HERE / "panel_render.js"), str(ROOT / "dashboard"), panel_file, str(ctx_file)],
                             capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert out.returncode == 0, "the panel threw: " + out.stderr[-600:]
    return json.loads(out.stdout)


def is_reference_tree() -> bool:
    """The reference tree holds the fact sheets that the learner template never gets."""
    return (ROOT / "facts" / "SCHEMA.md").exists()
