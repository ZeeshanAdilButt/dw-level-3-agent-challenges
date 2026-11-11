import pytest

from conftest import fixture_email, read_code, sign_in

pytestmark = pytest.mark.invariant


def test_signin_flow_gives_a_session_for_the_fixture_principal(client, capsys):
    email, principal = fixture_email()
    res = sign_in(client, capsys, email)
    assert res.status_code == 200
    assert res.json()["principal"] == {"id": principal.id, "role": "customer", "verified": True,
                                       "account_id": principal.account_id}
    assert "dw_session" in res.cookies
    me = client.get("/api/me")
    assert me.status_code == 200 and me.json()["principal"]["id"] == principal.id


def test_the_code_never_reaches_the_browser(client, capsys):
    email, _ = fixture_email()
    res = client.post("/api/signin", json={"email": email})
    code = read_code(capsys, email)
    assert code.isdigit() and len(code) == 6
    assert code not in res.text and code not in str(res.headers)


def test_unknown_email_gets_the_same_answer_and_no_code(client, capsys):
    known, _ = fixture_email()
    a = client.post("/api/signin", json={"email": known}).json()
    capsys.readouterr()
    b = client.post("/api/signin", json={"email": "nobody@nowhere.example"}).json()
    assert a == b
    assert "one-time code" not in capsys.readouterr().out


def test_wrong_code_is_refused_and_a_code_works_once(client, capsys):
    email, _ = fixture_email()
    client.post("/api/signin", json={"email": email})
    code = read_code(capsys, email)
    wrong = "000000" if code != "000000" else "111111"
    assert client.post("/api/verify", json={"email": email, "code": wrong}).status_code == 401
    assert client.post("/api/verify", json={"email": email, "code": code}).status_code == 200
    assert client.post("/api/verify", json={"email": email, "code": code}).status_code == 401


def test_too_many_wrong_codes_burn_the_code(client, capsys):
    email, _ = fixture_email()
    client.post("/api/signin", json={"email": email})
    code = read_code(capsys, email)
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(6):
        client.post("/api/verify", json={"email": email, "code": wrong})
    assert client.post("/api/verify", json={"email": email, "code": code}).status_code == 401


def test_chat_needs_a_session(client):
    assert client.post("/api/chat", json={"message": "hello"}).status_code == 401


def test_signout_ends_the_session(client, capsys):
    email, _ = fixture_email()
    sign_in(client, capsys, email)
    assert client.post("/api/signout").status_code == 200
    assert client.get("/api/me").status_code == 401


def test_session_chat_passes_the_session_principal_and_ignores_a_forged_one(client, capsys, agent):
    email, principal = fixture_email()
    sign_in(client, capsys, email)
    body = {"message": "What does Pro cost?", "conversation_id": "c1", "request_id": "r1",
            "principal": {"id": "someone-else", "role": "staff", "verified": True, "account_id": "acct-9999"}}
    res = client.post("/api/chat", json=body)
    assert res.status_code == 200
    seen = agent.seen[-1]
    assert seen.principal.id == principal.id and seen.principal.role == "customer"
    assert seen.text == "What does Pro cost?" and seen.conversation_id == "c1" and seen.request_id == "r1"
    assert "eval" not in res.json()


def test_a_cited_document_opens_only_in_the_session_that_was_cited(client, capsys):
    email, _ = fixture_email()
    sign_in(client, capsys, email)
    assert client.get("/api/docs/doc-pricing-table").status_code == 404   # not cited yet
    client.post("/api/chat", json={"message": "hi", "request_id": "r1"})
    doc = client.get("/api/docs/doc-pricing-table")
    assert doc.status_code == 200 and "Plans and pricing" in doc.json()["title"]
    assert client.get("/api/docs/..%2f..%2fINTERFACES").status_code == 404


def test_core_missing_gives_a_clear_error_not_a_crash(runs_dir, capsys, monkeypatch):
    from fastapi.testclient import TestClient
    from app.adapters.chat import CoreUnavailable, create_app
    from conftest import ROOT

    def broken():
        raise CoreUnavailable("app/core.py could not be imported (ImportError: no module named x)")

    monkeypatch.delenv("DW_TEST_MODE", raising=False)
    c = TestClient(create_app(root=ROOT, runs_dir=runs_dir, agent_factory=broken))
    email, _ = fixture_email()
    sign_in(c, capsys, email)
    res = c.post("/api/chat", json={"message": "hello"})
    assert res.status_code == 503
    assert res.json()["error"] == "agent_core_unavailable" and "app/core.py" in res.json()["detail"]
    assert c.get("/health").status_code == 200


@pytest.mark.parametrize("pack,role", [("quillon", "customer"), ("quillon", "prospect"), ("juniper", "patient"),
                                       ("saltmarsh", "policyholder")])
def test_every_pack_has_a_fixture_email_for_each_role(pack, role):
    email, principal = fixture_email(pack, role)
    assert "@" in email and principal.id
    assert principal.verified is (role != "prospect")
