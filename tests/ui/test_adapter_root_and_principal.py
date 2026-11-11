"""The chat adapter reads the settings of the root it was given, and builds a test principal's id the way the harness does."""
import json

from conftest import ROOT  # noqa: F401  (puts the repository on the path)

from app.adapters.chat import load_flat_settings


def test_the_adapter_reads_the_settings_of_its_own_root(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings.toml").write_text('[run]\npack = "juniper"\ntop_k = 7\n', encoding="utf-8")
    s = load_flat_settings(tmp_path)
    assert s["pack"] == "juniper" and s["top_k"] == 7


def test_an_inline_test_principal_gets_the_same_id_as_in_the_harness(client, agent, monkeypatch):
    from harness.cases import resolve_principal
    monkeypatch.setenv("DW_TEST_MODE", "1")
    monkeypatch.setenv("DW_EXAM_TOKEN", "t0k")
    for inline in ({"role": "customer", "verified": True, "account_id": "acct-1001"}, {"role": "prospect", "verified": False}):
        res = client.post("/api/chat", json={"message": "hi", "conversation_id": "c1", "request_id": f"r{len(agent.seen)}"},
                          headers={"X-Test-Principal": json.dumps(inline), "X-Exam-Token": "t0k"})
        assert res.status_code == 200
        assert agent.seen[-1].principal.id == resolve_principal(dict(inline), {})["id"]
