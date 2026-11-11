"""Paid hosted runs ask first, and the .env loader fills only variables that are not set."""
import os

from harness import envfile
from harness import run as run_mod

HOSTED = {"topology": "single", "tools": "off", "rules": "off", "hosted_model": "claude-haiku-5-5"}


def test_estimate_counts_calls_by_topology_and_rules():
    assert run_mod.estimate_hosted(HOSTED, 148)["calls"] == 148
    assert run_mod.estimate_hosted({**HOSTED, "topology": "router_specialists_reviewer"}, 10)["calls"] == 40
    assert run_mod.estimate_hosted({**HOSTED, "rules": "on"}, 10, repeat=3)["calls"] == 60
    assert run_mod.estimate_hosted(HOSTED, 148)["usd"] > 0


def test_confirm_asks_unless_yes(capsys):
    assert run_mod.confirm_paid(HOSTED, 10, 1, yes=True, ask=lambda _: 1 / 0) is True
    assert run_mod.confirm_paid(HOSTED, 10, 1, yes=False, ask=lambda _: "y") is True
    assert run_mod.confirm_paid(HOSTED, 10, 1, yes=False, ask=lambda _: "") is False
    out = capsys.readouterr().out
    assert "about 10 calls" in out and "estimated $" in out


def test_env_loader_never_overwrites(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text("# comment\nDW_T_ONE=1\nDW_T_TWO='two'\n\nDW_T_SET=from-file\n", encoding="utf-8")
    monkeypatch.delenv("DW_T_ONE", raising=False)
    monkeypatch.delenv("DW_T_TWO", raising=False)
    monkeypatch.setenv("DW_T_SET", "from-env")
    filled = envfile.load_env(f)
    try:
        assert sorted(filled) == ["DW_T_ONE", "DW_T_TWO"]
        assert os.environ["DW_T_TWO"] == "two" and os.environ["DW_T_SET"] == "from-env"
    finally:
        os.environ.pop("DW_T_ONE", None)
        os.environ.pop("DW_T_TWO", None)


def test_report_check_ignores_html_comments(tmp_path):
    from harness import report_check
    md = "Plain text.\n<!-- [99% answer success](runs/missing.json#x.y) -->\n"
    problems, n, _ = report_check.check_text(md, tmp_path)
    assert problems == [] and n == 0
