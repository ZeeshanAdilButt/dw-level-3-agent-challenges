import json

import pytest

pytestmark = pytest.mark.invariant

TOKEN = "exam-token-for-tests"


def chat(client, headers=None, **extra):
    body = {"message": "hello", "conversation_id": "c1", "request_id": "r1"}
    body.update(extra)
    return client.post("/api/chat", json=body, headers=headers or {})


def test_header_is_refused_when_test_mode_is_off(client, monkeypatch):
    monkeypatch.setenv("DW_EXAM_TOKEN", TOKEN)
    res = chat(client, {"X-Test-Principal": "acct-1001-owner", "X-Exam-Token": TOKEN})
    assert res.status_code == 403


@pytest.mark.parametrize("headers", [
    {"X-Test-Principal": "acct-1001-owner"},
    {"X-Test-Principal": "acct-1001-owner", "X-Exam-Token": "wrong"},
    {"X-Test-Principal": "acct-1001-owner", "X-Exam-Token": ""},
])
def test_header_is_refused_in_test_mode_without_the_exam_token(client, monkeypatch, headers):
    monkeypatch.setenv("DW_TEST_MODE", "1")
    monkeypatch.setenv("DW_EXAM_TOKEN", TOKEN)
    assert chat(client, headers).status_code == 403


def test_an_empty_server_token_never_matches_an_empty_header(client, monkeypatch):
    monkeypatch.setenv("DW_TEST_MODE", "1")
    monkeypatch.delenv("DW_EXAM_TOKEN", raising=False)
    assert chat(client, {"X-Test-Principal": "acct-1001-owner", "X-Exam-Token": ""}).status_code == 403


def test_test_mode_must_be_exactly_one(client, monkeypatch):
    monkeypatch.setenv("DW_TEST_MODE", "true")
    monkeypatch.setenv("DW_EXAM_TOKEN", TOKEN)
    assert chat(client, {"X-Test-Principal": "acct-1001-owner", "X-Exam-Token": TOKEN}).status_code == 403


def test_header_with_token_in_test_mode_sets_the_principal_and_returns_the_eval_block(client, monkeypatch, agent):
    monkeypatch.setenv("DW_TEST_MODE", "1")
    monkeypatch.setenv("DW_EXAM_TOKEN", TOKEN)
    res = chat(client, {"X-Test-Principal": "acct-1001-owner", "X-Exam-Token": TOKEN})
    assert res.status_code == 200
    assert agent.seen[-1].principal.id == "acct-1001-owner" and agent.seen[-1].principal.verified is True
    body = res.json()
    assert body["eval"]["raw_reply"] == "fake reply" and body["eval"]["ranked_hit_ids"] == ["doc-x#0"]


def test_test_mode_with_a_session_still_returns_the_eval_block(client, monkeypatch, capsys):
    from conftest import fixture_email, sign_in
    email, _ = fixture_email()
    sign_in(client, capsys, email)
    monkeypatch.setenv("DW_TEST_MODE", "1")
    assert "eval" in chat(client).json()


def test_header_can_name_an_inline_principal_as_json(client, monkeypatch, agent):
    monkeypatch.setenv("DW_TEST_MODE", "1")
    monkeypatch.setenv("DW_EXAM_TOKEN", TOKEN)
    who = {"id": "prospect-02", "role": "prospect", "verified": False, "account_id": None}
    res = chat(client, {"X-Test-Principal": json.dumps(who), "X-Exam-Token": TOKEN})
    assert res.status_code == 200 and agent.seen[-1].principal.role == "prospect"
    assert agent.seen[-1].principal.verified is False


def test_unknown_test_principal_is_a_400(client, monkeypatch):
    monkeypatch.setenv("DW_TEST_MODE", "1")
    monkeypatch.setenv("DW_EXAM_TOKEN", TOKEN)
    assert chat(client, {"X-Test-Principal": "nobody", "X-Exam-Token": TOKEN}).status_code == 400


def test_without_a_header_test_mode_does_not_skip_sign_in(client, monkeypatch):
    monkeypatch.setenv("DW_TEST_MODE", "1")
    monkeypatch.setenv("DW_EXAM_TOKEN", TOKEN)
    assert chat(client, {"X-Exam-Token": TOKEN}).status_code == 401


def test_a_retry_with_the_same_request_id_reaches_the_core_unchanged(client, monkeypatch, agent):
    monkeypatch.setenv("DW_TEST_MODE", "1")
    monkeypatch.setenv("DW_EXAM_TOKEN", TOKEN)
    h = {"X-Test-Principal": "acct-1001-owner", "X-Exam-Token": TOKEN}
    chat(client, h, request_id="same")
    chat(client, h, request_id="same")
    assert [m.request_id for m in agent.seen] == ["same", "same"]


@pytest.mark.parametrize("bad", [{"message": ""}, {"message": "x" * 5000}, {"request_id": "has space"},
                                 {"conversation_id": "a/b"}])
def test_bad_input_is_a_400(client, monkeypatch, bad):
    monkeypatch.setenv("DW_TEST_MODE", "1")
    monkeypatch.setenv("DW_EXAM_TOKEN", TOKEN)
    h = {"X-Test-Principal": "acct-1001-owner", "X-Exam-Token": TOKEN}
    assert chat(client, h, **bad).status_code == 400
