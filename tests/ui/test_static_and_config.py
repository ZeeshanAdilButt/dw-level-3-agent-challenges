import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

from conftest import ROOT

pytestmark = pytest.mark.invariant

PANELS = ["run-history", "headline", "run-tree", "diff", "recall-slices", "context-tokens", "correctness",
          "must-pass", "quality-cost", "security", "trace", "failures", "two-path"]
DASH = chr(0x2014) + chr(0x2013)


def test_chat_ui_and_dashboard_are_served(client):
    chat = client.get("/")
    assert chat.status_code == 200 and "Company agent chat" in chat.text
    dash = client.get("/dashboard")
    assert dash.status_code == 200 and "Run dashboard" in dash.text
    for asset in ["/static/base.css", "/static/chat.js", "/static/chat.css", "/dashboard/dashboard.js",
                  "/dashboard/lib.js", "/dashboard/dashboard.css"] + [f"/dashboard/panels/{p}.js" for p in PANELS]:
        assert client.get(asset).status_code == 200, asset


def test_every_panel_is_loaded_by_the_dashboard_page():
    html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
    for p in PANELS:
        assert f"/dashboard/panels/{p}.js" in html


def test_every_panel_registers_itself_with_a_title_and_a_lab():
    for p in PANELS:
        text = (ROOT / "dashboard" / "panels" / f"{p}.js").read_text(encoding="utf-8")
        assert f'id: "{p}"' in text and "title:" in text and "lab:" in text and "Dashboard.register" in text


def test_your_turn_blocks_are_balanced_and_named():
    for p in PANELS:
        text = (ROOT / "dashboard" / "panels" / f"{p}.js").read_text(encoding="utf-8")
        starts = re.findall(r"// YOUR TURN start: (\S.*)", text)
        ends = re.findall(r"// YOUR TURN end", text)
        assert len(starts) == len(ends)
        assert len(starts) <= 1
        if p in ("run-history", "headline"):
            assert starts == [], "the two starter tables are shipped, not gaps"
        elif "Dashboard.notBuilt(el," in text:           # a starter: the block was replaced by the placeholder
            assert starts == [], p
        else:                                            # the reference: one named block
            assert len(starts) == 1 and re.match(r"Lab \d", starts[0]), p


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_every_script_is_valid_javascript():
    files = [*(ROOT / "dashboard").rglob("*.js"), ROOT / "app" / "static" / "chat.js"]
    for f in files:
        res = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        assert res.returncode == 0, f"{f}: {res.stderr}"


def test_no_em_or_en_dashes_in_the_ui_tooling_or_config():
    paths = [*(ROOT / "app" / "static").rglob("*"), *(ROOT / "dashboard").rglob("*"), *(ROOT / "config").rglob("*"),
             *(ROOT / ".github").rglob("*"), ROOT / "app" / "adapters" / "chat.py", ROOT / "app" / "__main__.py",
             *(ROOT / "tools").glob("doctor.py"), *(ROOT / "tools").glob("make_starter.py"),
             *(ROOT / "tools").glob("export_scan.py"), *(ROOT / "tests" / "ui").glob("*.py")]
    for f in paths:
        if f.is_file():
            text = f.read_text(encoding="utf-8")
            assert not any(ch in text for ch in DASH), f


def test_ui_follows_the_house_style():
    css = "".join(p.read_text(encoding="utf-8") for p in [*(ROOT / "app" / "static").glob("*.css"),
                                                           *(ROOT / "dashboard").glob("*.css")])
    for banned in ["gradient", "box-shadow", "text-shadow", "backdrop-filter", "blur("]:
        assert banned not in css, banned
    assert "@media (max-width" in css                      # a small-screen rule exists
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8") + \
        (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
    assert 'name="viewport"' in html


def test_settings_toml_has_every_key_with_its_default():
    raw = tomllib.loads((ROOT / "config" / "settings.toml").read_text(encoding="utf-8"))
    flat = {}
    for section in raw.values():
        flat.update(section)
    assert set(raw) == {"lab1", "lab2", "lab3", "lab4", "lab5", "lab6", "lab7", "lab8", "clinic"}
    assert flat == {
        "pack": "quillon", "model_path": "local", "model": "qwen3:4b-instruct", "hosted_model": "",
        "embed_model": "nomic-embed-text", "temperature": 0.2, "top_k": 5, "chunker": "fixed", "chunk_size": 400,
        "overlap": 0, "retriever": "bm25", "context": "none", "neighbours_n": 1, "context_token_limit": 3000,
        "authority_rule": "off", "tools": "off", "rules": "off", "topology": "single", "defences": [],
        "trace_steps": "off", "region": "Port Avery", "emergency_number": "112"}
    assert 0 <= flat["overlap"] < flat["chunk_size"]


def test_prices_toml_is_dated_and_complete():
    prices = tomllib.loads((ROOT / "config" / "prices.toml").read_text(encoding="utf-8"))
    assert prices["date"] == "2026-11-06"
    for name, m in prices["models"].items():
        assert {"input", "output", "hosted_equivalent_input", "hosted_equivalent_output"} <= set(m), name
    assert prices["models"]["qwen3:4b-instruct"]["input"] == 0 and prices["models"]["qwen3:4b-instruct"]["output"] == 0
    assert prices["models"]["qwen3:4b-instruct"]["hosted_equivalent_input"] > 0


def test_ids_yaml_matches_the_packs_and_the_attack_files():
    ids = yaml.safe_load((ROOT / "config" / "ids.yaml").read_text(encoding="utf-8"))
    assert [c["slug"] for c in ids["companies"]] == ["quillon", "juniper", "saltmarsh"]
    assert ids["attack_families"] == ["doc-injection", "message-injection", "other-person", "internal-content",
                                      "system-prompt", "domain-harm"]
    for company in ids["companies"]:
        assert (ROOT / company["pack_folder"]).is_dir()
        rows = [json.loads(line) for line in (ROOT / company["pack_folder"] / "eval" / "attacks.jsonl").read_text(
            encoding="utf-8").splitlines() if line.strip()]
        assert {r["family"] for r in rows} <= set(ids["attack_families"])
    assert set(ids["reference_runs"]) == {f"lab{n}" for n in range(1, 9)}


def test_ci_workflow_names_the_two_jobs_and_uses_no_secrets():
    ci = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    assert set(ci["jobs"]) == {"tests", "harness-validate"}
    assert ci["jobs"]["tests"]["name"] == "tests" and ci["jobs"]["harness-validate"]["name"] == "harness-validate"
    raw = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "secrets." not in raw and "python -m harness validate" in raw and "pytest" in raw
    assert ci["env"]["DW_MODEL_PATH"] == "stub"
