"""Capstone part 3: the agent online for the checker. The shipped parts (/health, the token check, exam mode, the mock
address) are checked on a fake agent, with no network and no model. The log entry is checked in a learner repository only
(one with LAB-LOG.md at its root).

On the starter the log check fails with: AssertionError: no online entry
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.adapters.chat import AgentHolder, create_app, load_principals  # noqa: E402
from app.types import EvalBlock, Reply  # noqa: E402
from mock_api import HttpMockClient, MockClient  # noqa: E402

LEARNER_REPO = (ROOT / "LAB-LOG.md").exists()
TOKEN = "token-for-this-test-only"
PRINCIPAL = sorted(load_principals(ROOT, "quillon")[0])[0]


class FakeAgent:
    def handle(self, msg):
        block = EvalBlock(raw_reply="fake reply", ranked_hit_ids=["doc-pricing-table#0"], delivered_doc_ids=["doc-pricing-table"])
        return Reply(text="fake reply", citations=["doc-pricing-table"], actions=[], pending=None, handoff=None, usage=[],
                     cost_usd=0.0, latency_ms=1.0, trace_id="t-1", eval=block)


@pytest.fixture
def client(tmp_path, monkeypatch):
    for name in ("DW_TEST_MODE", "DW_EXAM_TOKEN", "MOCK_API_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DW_COMMIT", "abc1234")
    return TestClient(create_app(root=ROOT, runs_dir=tmp_path / "runs", agent_factory=lambda: FakeAgent()))


def expected_commit() -> str:
    """git HEAD in a repository (DW_COMMIT cannot override it there); DW_COMMIT only for a copy with no .git."""
    if not (ROOT / ".git").exists():
        return "abc1234"
    out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def ask(client, headers=None):
    return client.post("/api/chat", json={"text": "How much is Pro per seat?", "request_id": "r1", "conversation_id": "c1"},
                       headers=headers or {})


def test_health_reports_status_commit_fingerprint_and_model(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert {"commit", "fingerprint", "model"} <= set(body)
    assert body["commit"] == expected_commit()              # the commit the checker compares with your submission
    assert body["fingerprint"] == "none"                    # no kept run in this empty runs folder


def test_health_needs_no_token(client, monkeypatch):
    monkeypatch.setenv("DW_TEST_MODE", "1")
    monkeypatch.setenv("DW_EXAM_TOKEN", TOKEN)
    assert client.get("/health").status_code == 200


def test_in_exam_mode_the_test_header_without_the_token_is_refused(client, monkeypatch):
    monkeypatch.setenv("DW_TEST_MODE", "1")
    monkeypatch.setenv("DW_EXAM_TOKEN", TOKEN)
    for headers in ({"X-Test-Principal": PRINCIPAL}, {"X-Test-Principal": PRINCIPAL, "X-Exam-Token": "wrong"}):
        res = ask(client, headers)
        assert res.status_code == 403
        assert "test_principal_refused" in res.text


def test_in_exam_mode_the_token_lets_the_header_through_and_the_reply_carries_the_eval_block(client, monkeypatch):
    monkeypatch.setenv("DW_TEST_MODE", "1")
    monkeypatch.setenv("DW_EXAM_TOKEN", TOKEN)
    res = ask(client, {"X-Test-Principal": PRINCIPAL, "X-Exam-Token": TOKEN})
    assert res.status_code == 200
    assert res.json()["eval"]["ranked_hit_ids"] == ["doc-pricing-table#0"]


def test_with_test_mode_off_the_header_is_never_honoured(client, monkeypatch):
    monkeypatch.setenv("DW_EXAM_TOKEN", TOKEN)                # a token alone is not enough
    res = ask(client, {"X-Test-Principal": PRINCIPAL, "X-Exam-Token": TOKEN})
    assert res.status_code == 403


def test_without_the_header_a_visitor_must_sign_in(client):
    assert ask(client).status_code == 401


def test_without_the_mock_address_the_tools_use_your_own_mock(monkeypatch):
    monkeypatch.delenv("MOCK_API_URL", raising=False)
    assert isinstance(AgentHolder._make_mock(ROOT / "packs" / "quillon"), MockClient)


def test_the_http_mock_client_keeps_the_address_it_is_given():
    mock = HttpMockClient("https://mock.example.test/", "live")
    assert mock.base == "https://mock.example.test" and mock.namespace == "live"


def test_with_the_mock_address_set_the_tools_call_that_address(monkeypatch):
    monkeypatch.setenv("MOCK_API_URL", "https://mock.example.test/")
    mock = AgentHolder._make_mock(ROOT / "packs" / "quillon")
    assert isinstance(mock, HttpMockClient) and mock.base == "https://mock.example.test"


def log_entry(text: str):
    """The lines of the first LAB-LOG.md entry whose heading mentions online, or None."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("#") and "online" in line.lower():
            level = len(line) - len(line.lstrip("#"))
            body = []
            for nxt in lines[i + 1:]:
                if nxt.startswith("#") and len(nxt) - len(nxt.lstrip("#")) <= level:
                    break
                body.append(nxt)
            return "\n".join(body)
    return None


def check_log(text: str) -> None:
    entry = log_entry(text)
    assert entry is not None and entry.strip(), "no online entry"
    assert re.search(r"\d{4}-\d{2}-\d{2}", entry), "the online entry needs a date (for example 2026-11-08)"
    assert re.search(r"tunnel|host", entry, re.I), "say whether you used a tunnel or a host"
    assert "trycloudflare.com" not in text and "DW_EXAM_TOKEN=" not in text, "never write the address or the token in the log"


def test_the_log_check_accepts_a_good_entry_and_refuses_a_bad_one():
    good = "# Log\n\n## Online for the checker\n\n2026-11-08, quick tunnel. Check again: that the commit on /health matches.\n\n## Next\n\nx\n"
    check_log(good)
    with pytest.raises(AssertionError, match="no online entry"):
        check_log("# Log\n\n## Lab 8\n\ntext\n")
    with pytest.raises(AssertionError, match="address or the token"):
        check_log(good + "\nmy address is https://abc.trycloudflare.com\n")
    with pytest.raises(AssertionError, match="date"):
        check_log("## Online\n\nused a tunnel\n")


@pytest.mark.skipif(not LEARNER_REPO, reason="runs in a learner repository only")
def test_my_log_has_an_online_entry():
    check_log((ROOT / "LAB-LOG.md").read_text(encoding="utf-8"))
