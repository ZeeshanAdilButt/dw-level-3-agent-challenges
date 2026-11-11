"""Lab 6, part 1: the router and the specialists. Fixed fixtures and the stub model only.

On the starter these fail with `NotImplementedError: YOUR TURN: ...` from the router or the specialist.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fixtures_teams import ANA, PATIENT, make_agent, msg  # noqa: E402

from app.agents.base import Turn  # noqa: E402
from app.agents.router import route  # noqa: E402
from app.agents.specialists import AREAS, area_types  # noqa: E402
from app.security import access  # noqa: E402
from app.trace import Tracer  # noqa: E402

PRICE_Q = "How much is Pro per seat if we pay every month?"
BOTH_Q = "What does Pro cost and what is the minimum contract term?"


def test_the_router_returns_a_note_for_each_specialist_it_picks():
    agent = make_agent(topology="router_specialists")
    agent.model.replies = [json.dumps([{"area": "sales", "note": "Give the monthly price."},
                                       {"area": "contract", "note": "Give the minimum term."}])]
    reply = agent.handle(msg(BOTH_Q, ANA))
    assert [c["step"] for c in agent.model.calls][:3] == ["router", "specialist:sales", "specialist:contract"]
    assert "Give the monthly price." in agent.model.calls[1]["messages"][0]["content"]
    assert "Give the minimum term." in agent.model.calls[2]["messages"][0]["content"]
    assert reply.text


def test_the_router_falls_back_to_one_area_when_its_reply_is_not_usable():
    agent = make_agent(topology="router_specialists")
    agent.model.replies = ["I think this is about prices."]                       # not JSON
    agent.handle(msg(PRICE_Q, ANA))
    assert [c["step"] for c in agent.model.calls][:2] == ["router", "specialist:sales"]


def test_a_specialist_sees_only_its_areas_documents():
    agent = make_agent(topology="router_specialists")
    sales, contract = area_types(agent, "sales"), area_types(agent, "contract")
    assert "pricing" in sales and "clause" in contract and not sales & contract
    reply = agent.handle(msg(PRICE_Q, ANA))
    delivered_types = {agent.index.docs[d].meta["type"] for d in reply.eval.delivered_doc_ids}
    assert delivered_types and delivered_types <= sales


def test_a_specialist_is_given_only_its_areas_tools():
    agent = make_agent(topology="router_specialists", tools="on")
    agent.model.replies = [json.dumps([{"area": "sales", "note": "Answer the price question."}])]
    agent.handle(msg(PRICE_Q, ANA))
    offered = {t["function"]["name"] for t in agent.model.calls[1]["tools"]}
    assert offered == set(AREAS["quillon"]["sales"]["tools"])
    agent = make_agent(topology="router_specialists", tools="on")
    agent.model.replies = [json.dumps([{"area": "sales", "note": "Check the account."}]),
                           {"text": "", "tool_calls": [{"name": "lookup_account", "arguments": {}}]}]
    reply = agent.handle(msg("Please check my account for me.", ANA))
    refused = [c for c in reply.eval.attempted_tool_calls if c["name"] == "lookup_account"]
    assert refused and refused[0]["refused"] and "not available to this specialist" in refused[0]["reason"]


def test_the_principal_is_passed_by_the_core_and_never_inside_a_note():
    agent = make_agent(topology="router_specialists")
    agent.model.replies = [json.dumps([{"area": "sales", "note": f"Help {ANA.id} on {ANA.account_id} with the price."}])]
    agent.handle(msg(PRICE_Q, ANA))
    router_in = json.dumps(agent.model.calls[0]["messages"])
    assert ANA.id not in router_in and ANA.account_id not in router_in            # the router never sees the principal
    note_part = agent.model.calls[1]["messages"][0]["content"].split("note for you:")[-1]
    assert ANA.id not in note_part and ANA.account_id not in note_part            # and the note was cleaned
    in_user = agent.model.calls[1]["messages"][1]["content"].split("Note from the router:")[-1]
    assert ANA.id not in in_user and ANA.account_id not in in_user                # the same note, where the message carries it
    # route() on its own: a note that held only ids ends up empty
    agent = make_agent(topology="router_specialists")
    agent.model.replies = [json.dumps([{"area": "sales", "note": f"{ANA.id}{ANA.account_id}"}])]
    m = msg(PRICE_Q, ANA)
    turn = Turn(msg=m, tracer=Tracer(m.request_id), state={}, history=[], req_hash="h")
    assert route(agent, turn)[0]["note"] == ""


def test_access_and_the_lab_5_rules_still_run_for_every_specialist_call(monkeypatch):
    seen = []
    real = access.allowed

    def spy(item, principal):
        seen.append(item["kind"])
        return real(item, principal)
    monkeypatch.setattr(access, "allowed", spy)
    agent = make_agent(topology="router_specialists", defences=["access"], context="link_hop")
    agent.handle(msg(PRICE_Q, ANA))
    assert "chunk" in seen and "history" in seen                                  # asked on every retrieved item
    clinic = make_agent("juniper", tools="on", rules="on", topology="router_specialists")
    reply = clinic.handle(msg("My chest feels funny and my arm is numb.", PATIENT))
    assert "112" in reply.text and clinic.mock.state()["handoffs"]                # the rules layer ran before any team member
    insurer = make_agent("saltmarsh", rules="on", topology="router_specialists")
    # the classifier is called first on this pack, so the script starts with its reply
    insurer.model.replies = ['{"category": "none"}', '[{"area": "cover", "note": "x"}]',
                             "You are covered and it will definitely be paid. [doc-hw-c41-storm]"]
    reply = insurer.handle(msg("Is storm damage covered?"))
    assert "payout-wording" in reply.eval.rule_hits                               # the reply rules check ran on the merged reply


def test_the_merged_answer_cites_the_union_of_the_specialists_sources():
    agent = make_agent(topology="router_specialists")
    agent.model.replies = [json.dumps([{"area": "sales", "note": "price"}, {"area": "contract", "note": "term"}]),
                           "Pro costs $38 per seat per month. [doc-pricing-table]",
                           "The minimum term is twelve months. [doc-clause-term]",
                           "Pro costs $38 per seat per month and the term is twelve months."]   # the merge dropped both markers
    reply = agent.handle(msg(BOTH_Q, ANA))
    assert [c["step"] for c in agent.model.calls] == ["router", "specialist:sales", "specialist:contract", "merge"]
    assert reply.citations == ["doc-pricing-table", "doc-clause-term"]


def test_every_model_call_appears_in_the_usage_record():
    agent = make_agent(topology="router_specialists")
    agent.model.replies = [json.dumps([{"area": "sales", "note": "price"}, {"area": "contract", "note": "term"}])]
    reply = agent.handle(msg(BOTH_Q, ANA))
    assert len(reply.usage) == len(agent.model.calls) == 4
    assert [u["step"] for u in reply.usage] == ["router", "specialist:sales", "specialist:contract", "merge"]
