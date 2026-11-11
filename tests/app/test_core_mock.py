"""The mock API: state per namespace, reset, receipts, idempotency keys, and the FastAPI server."""
import threading
import time

import pytest
import uvicorn
from fixtures_app import ANA, ELEANOR, PACKS, PATIENT, PROSPECT
from fastapi.testclient import TestClient

from mock_api import HttpMockClient, MockClient
from mock_api.server import create_app

QUOTE = {"account_id": "acct-1001", "plan": "PLN-TEAM-25", "seats": 20, "term": "monthly"}


def test_receipts_state_reset_and_namespaces():
    a, b = MockClient(PACKS / "quillon", "ns-a"), MockClient(PACKS / "quillon", "ns-b")
    r = a.call("create_quote", QUOTE, ANA, "k1")
    assert r["ok"] and r["receipt_id"].startswith("rcpt-ns-a-") and r["result"]["list_total_usd"] == 580.0 and r["replayed"] is False
    assert a.state()["counts"]["quotes_created"] == 1 and b.state()["counts"]["quotes_created"] == 0     # state is per namespace
    again = a.call("create_quote", QUOTE, ANA, "k1")
    assert again["replayed"] is True and again["receipt_id"] == r["receipt_id"] and a.state()["counts"]["quotes_created"] == 1
    assert a.call("create_quote", QUOTE, ANA, "k2")["replayed"] is False and a.state()["counts"]["quotes_created"] == 2
    assert [x["tool"] for x in a.state()["receipts"]] == ["create_quote", "create_quote"]
    a.reset()
    assert a.state()["counts"]["quotes_created"] == 0 and a.state()["receipts"] == [] and a.state()["read_only"] is True
    assert a.call("create_quote", QUOTE, ANA, "k1")["replayed"] is False                                    # reset forgets keys too


def test_a_key_cannot_be_reused_by_another_principal_or_tool():
    m = MockClient(PACKS / "quillon", "ns")
    m.call("create_quote", QUOTE, ANA, "shared")
    other = m.call("lookup_account", {}, ANA, "shared")
    assert other["ok"] is False and other["error"] == "idempotency_key_reused"


def test_the_company_rules_the_tools_enforce():
    q = MockClient(PACKS / "quillon", "q")
    r = q.call("create_quote", {**QUOTE, "discount_pct": 11}, ANA, "a")
    assert r["error"] == "needs_approval" and q.state()["counts"]["quotes_created"] == 0
    assert q.call("create_quote", {**QUOTE, "discount_pct": 10}, ANA, "b")["result"]["net_total_usd"] == 522.0
    assert q.call("lookup_account", {}, PROSPECT, "c")["ok"] is False
    assert q.call("lookup_account", {"account_id": "acct-1004"}, ANA, "d")["error"] == "forbidden"
    j = MockClient(PACKS / "juniper", "j")
    assert j.call("hand_off", {"reason": "red_flag", "urgency": "soon", "note": ""}, PATIENT, "e")["error"] == "red_flag_is_urgent"
    assert j.call("hand_off", {"reason": "red_flag", "urgency": "urgent", "note": "x"}, PATIENT, "f")["result"]["pickup"] == "5 minutes"
    s = MockClient(PACKS / "saltmarsh", "s")
    assert s.call("lookup_policy", {"policy_number": "SM-H-100231", "date_of_birth": "1981-03-15"}, PROSPECT, "g")["error"] == "identity_not_verified"
    assert s.call("lookup_policy", {"policy_number": "SM-H-999999", "date_of_birth": "1981-03-14"}, PROSPECT, "h")["error"] == "identity_not_verified"
    assert s.call("lookup_policy", {"policy_number": "SM-H-100231", "date_of_birth": "1981-03-14"}, ELEANOR, "i")["ok"]


def test_the_server_per_namespace_state_reset_and_idempotency():
    client = TestClient(create_app(PACKS))
    body = {"args": QUOTE, "principal": {"id": ANA.id, "role": "customer", "verified": True, "account_id": "acct-1001"}, "idempotency_key": "k1"}
    r = client.post("/ns/n1/tools/create_quote", json=body, headers={"X-DW-Pack": "quillon"}).json()
    assert r["ok"] and r["result"]["quote_id"]
    assert client.post("/ns/n1/tools/create_quote", json=body, headers={"X-DW-Pack": "quillon"}).json()["replayed"] is True
    assert client.get("/ns/n1/state", headers={"X-DW-Pack": "quillon"}).json()["counts"]["quotes_created"] == 1
    assert client.get("/ns/n2/state", headers={"X-DW-Pack": "quillon"}).json()["counts"]["quotes_created"] == 0
    assert client.post("/ns/n1/reset", headers={"X-DW-Pack": "quillon"}).json() == {"ok": True}
    assert client.get("/ns/n1/state", headers={"X-DW-Pack": "quillon"}).json()["counts"]["quotes_created"] == 0
    assert client.post("/ns/n1/tools/create_quote", json={"args": {}, "principal": {}, "idempotency_key": "x"}).status_code == 422
    assert client.get("/ns/n1/state", headers={"X-DW-Pack": "nope"}).status_code == 404


def test_http_mock_client_matches_the_in_process_client():
    app = create_app(PACKS)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8137, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    try:
        http = HttpMockClient("http://127.0.0.1:8137", "case-1", pack="quillon")
        local = MockClient(PACKS / "quillon", "case-1")
        a, b = http.call("create_quote", QUOTE, ANA, "k"), local.call("create_quote", QUOTE, ANA, "k")
        assert a["ok"] and a["result"] == b["result"] and http.call("create_quote", QUOTE, ANA, "k")["replayed"] is True
        assert http.state()["counts"]["quotes_created"] == 1
        http.reset()
        assert http.state()["counts"]["quotes_created"] == 0
    finally:
        server.should_exit = True
        thread.join(5)


def test_the_agent_works_against_the_http_client_too():
    from fixtures_app import Scripted, msg
    from app.core import Agent
    from app.settings import validate
    app = create_app(PACKS)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8138, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    try:
        s = validate({"model_path": "stub", "tools": "on"})
        agent = Agent(s, PACKS / "quillon", HttpMockClient("http://127.0.0.1:8138", "agent-ns"), Scripted(s))
        assert agent.mock.pack == "quillon"                                          # the agent tells the hosted mock which pack it is
        r = agent.handle(msg("Can you quote us 50 Pro seats on an annual term?", ANA))
        assert r.actions and r.actions[0]["receipt"]["ok"]
        assert agent.mock.state()["counts"]["quotes_created"] == 1
    finally:
        server.should_exit = True
        thread.join(5)
    pytest.importorskip("fastapi")
