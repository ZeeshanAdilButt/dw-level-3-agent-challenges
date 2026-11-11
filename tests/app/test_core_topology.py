"""Topologies: router and specialists, the reviewer, and that the core's checks still run for every call."""
import json

from fixtures_app import ANA, PROSPECT, STAFF, make_agent, msg

from app.agents.specialists import AREAS, area_types

PRICE_Q = "How much is Pro per seat if we pay every month?"


def names(reply):
    return [s["name"] for s in reply.eval.spans]


def test_the_router_picks_an_area_and_the_specialist_answers():
    agent = make_agent(topology="router_specialists")
    r = agent.handle(msg(PRICE_Q, ANA))
    assert [c["step"] for c in agent.model.calls] == ["router", "specialist:sales"]
    spans = {s["span_id"]: s for s in r.eval.spans}
    kinds = [s["name"] for s in spans.values()]
    assert kinds.count("router") == 1 and kinds.count("specialist") == 1 and kinds.count("model") == len(r.usage) == 2
    for s in spans.values():                                                    # the model calls sit inside the router and specialist spans
        if s["name"] == "model":
            assert spans[s["parent_id"]]["name"] in ("router", "specialist")
    assert r.citations


def test_a_specialist_sees_only_its_areas_documents():
    agent = make_agent(topology="router_specialists")
    sales = area_types(agent, "sales")
    contract = area_types(agent, "contract")
    assert not sales & contract and "pricing" in sales and "clause" in contract
    internal_types = {d.meta["type"] for d in agent.index.docs.values() if d.meta["audience"] == "internal"}
    assert internal_types <= contract                                            # "*" collects every type nobody lists
    r = agent.handle(msg(PRICE_Q, ANA))
    types = {agent.index.docs[d].meta["type"] for d in r.eval.delivered_doc_ids}
    assert types <= sales


def test_the_principal_is_passed_by_the_core_and_never_inside_a_note():
    agent = make_agent(topology="router_specialists")
    agent.model.replies = [json.dumps([{"area": "sales", "note": f"Help {ANA.id} on {ANA.account_id} with the price."}])]
    agent.handle(msg(PRICE_Q, ANA))
    router_in = json.dumps(agent.model.calls[0]["messages"])
    assert ANA.id not in router_in and ANA.account_id not in router_in           # the router never sees the principal
    specialist_system = agent.model.calls[1]["messages"][0]["content"]
    assert ANA.id not in specialist_system and "acct-1001" not in specialist_system.split("note for you:")[-1]


def test_two_specialists_are_merged_and_the_answer_cites_the_union():
    agent = make_agent(topology="router_specialists")
    agent.model.replies = [json.dumps([{"area": "sales", "note": "price"}, {"area": "contract", "note": "term"}]),
                           "Pro costs $38 per seat per month. [doc-pricing-table]", "The minimum term is twelve months. [doc-clause-term]",
                           "Pro costs $38 per seat per month and the minimum term is twelve months."]        # the merge dropped both markers
    r = agent.handle(msg("What does Pro cost and what is the minimum contract term?", ANA))
    assert [c["step"] for c in agent.model.calls] == ["router", "specialist:sales", "specialist:contract", "merge"]
    assert r.citations == ["doc-pricing-table", "doc-clause-term"]
    assert len(r.usage) == 4                                                       # every model call is in the usage


def test_allowed_and_the_rules_still_run_for_every_specialist_call():
    agent = make_agent("juniper", tools="on", rules="on", defences=["access"], topology="router_specialists")
    from fixtures_app import PATIENT
    r = agent.handle(msg("My chest feels funny and my arm is numb.", PATIENT))
    assert "call 112 now" in r.text and agent.mock.state()["handoffs"]               # the rules layer runs before any team member
    internal = {d for d, doc in agent.index.docs.items() if doc.meta["audience"] == "internal"}
    r = agent.handle(msg("How do I get a booking override or fee waiver?", PATIENT))
    assert not set(r.eval.delivered_doc_ids) & internal                              # access applies to the specialist's retrieval


def test_the_reviewer_passes_or_asks_for_one_revision_never_more():
    agent = make_agent(topology="router_specialists_reviewer")
    r = agent.handle(msg(PRICE_Q, ANA))
    assert [c["step"] for c in agent.model.calls] == ["router", "specialist:sales", "reviewer"] and "reviewer" in names(r)
    agent = make_agent(topology="router_specialists_reviewer")
    agent.model.replies = ['[{"area": "sales", "note": "x"}]', "Pro is $38 a month.",
                           json.dumps({"verdict": "revise", "feedback": "Cite the document."}), "Pro is $38 a month. [doc-pricing-table]",
                           json.dumps({"verdict": "revise", "feedback": "again"})]
    r = agent.handle(msg(PRICE_Q, ANA))
    steps = [c["step"] for c in agent.model.calls]
    assert steps == ["router", "specialist:sales", "reviewer", "revise"]             # one revision; the reviewer is not asked again
    assert r.citations == ["doc-pricing-table"] and len(r.usage) == 4                # the revision counts as an extra call


def test_the_reply_rules_check_still_runs_last_with_a_reviewer():
    agent = make_agent("saltmarsh", rules="on", topology="router_specialists_reviewer")
    agent.model.replies = ['[{"area": "cover", "note": "x"}]', "You are covered and it will definitely be paid. [doc-hw-c41-storm]",
                           json.dumps({"verdict": "pass"})]
    r = agent.handle(msg("Is storm damage covered?", PROSPECT))
    assert "payout-wording" in r.eval.rule_hits and "claims handler" in r.text


def test_every_area_names_real_tools():
    from app.tools import SPECS
    for pack, areas in AREAS.items():
        for area in areas.values():
            assert set(area["tools"]) <= set(SPECS[pack])
    assert STAFF  # keep the import used


def test_a_specialist_gets_its_note_and_documents_and_nothing_from_the_chat():
    from fixtures_app import PATIENT
    agent = make_agent("juniper", topology="router_specialists", tools="on")
    first, question = "I am Imelda and I want to ask about my insurer.", "How early must I stop eating before the fasting blood test?"
    agent.handle(msg(first, PATIENT, conv="c-team"))
    agent.model.replies = [json.dumps([{"area": "booking", "note": "Explain the fasting rule for the blood test."}])]
    agent.handle(msg(question, PATIENT, conv="c-team"))
    call = next(c for c in reversed(agent.model.calls) if c["step"].startswith("specialist:"))
    seen = json.dumps(call["messages"])
    assert [m["role"] for m in call["messages"]] == ["system", "user"]                   # no history lines
    assert first not in seen and question not in seen                                   # neither the earlier message nor the raw question
    assert "1984-03-14" not in seen and "Imelda" not in seen and PATIENT.account_id not in seen   # no principal block
    assert "Explain the fasting rule for the blood test." in call["messages"][-1]["content"]


def test_the_router_and_reviewer_take_the_first_valid_json_value_in_a_chatty_reply():
    from app.agents.base import first_json
    assert first_json('See [doc-a]. Picks: [{"area": "contract", "note": "term"}] and [note] after.', list) == [{"area": "contract", "note": "term"}]
    assert first_json('{"verdict": "revise", "feedback": "Cite it."} Also {not json}.', dict)["verdict"] == "revise"
    assert first_json("no json here", dict) is None

    agent = make_agent(topology="router_specialists")
    agent.model.replies = ['Area list: [{"area": "contract", "note": "term"}]. Ignore [this].']
    agent.handle(msg("What is the minimum contract term?", ANA))
    assert [c["step"] for c in agent.model.calls] == ["router", "specialist:contract"]   # a greedy match fell back to sales

    agent = make_agent(topology="router_specialists_reviewer")
    agent.model.replies = [json.dumps([{"area": "sales", "note": "price"}]), "Pro is $38. [doc-pricing-table]",
                           '{"verdict": "revise", "feedback": "Say per seat."} Notes: {draft ok}', "Pro is $38 per seat. [doc-pricing-table]"]
    agent.handle(msg(PRICE_Q, ANA))
    assert [c["step"] for c in agent.model.calls][-2:] == ["reviewer", "revise"]
