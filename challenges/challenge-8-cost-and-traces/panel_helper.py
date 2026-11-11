"""Draw one dashboard panel on fixed data, with node and a small fake page (panel_runner.js), and return what it drew."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def render_panel(panel: str, ctx: dict) -> dict:
    """`panel` is a file name under dashboard/panels/. Returns {"tables": [...], "notes": [...]}."""
    with tempfile.TemporaryDirectory() as tmp:
        ctx_file = Path(tmp) / "ctx.json"
        ctx_file.write_text(json.dumps(ctx), encoding="utf-8")
        done = subprocess.run(["node", str(HERE / "panel_runner.js"), str(ROOT / "dashboard" / "panels" / panel), str(ctx_file)],
                              capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert done.returncode == 0, "the panel threw an error: " + done.stderr[:600]
    return json.loads(done.stdout)
