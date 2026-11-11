"""A revision after two specialists: it sees every delivered document and every tool result, and it cites only what the
revised text cites."""
import json

from fixtures_app import ANA, make_agent, msg

from app.prompts import parse_documents

ROUTER = json.dumps([{"area": "sales", "note": "price"}, {"area": "contract", "note": "renewal"}])


def first_doc(messages):
    return parse_documents(messages[-1]["content"])[0][0]


def test_a_revision_after_two_specialists_sees_both_and_cites_only_the_revised_text():
    seen = {}

    def specialist(m, t, s):
        seen.setdefault("drafts", []).append(first_doc(m))
        return f"Part {len(seen['drafts'])}. [{seen['drafts'][-1]}]"

    def revise(m, t, s):
        seen["revise_in"] = m[-1]["content"]
        return f"Revised. [{seen['drafts'][1]}]"

    agent = make_agent(topology="router_specialists_reviewer", tools="on")
    agent.model.replies = [ROUTER, specialist, specialist, "Part 1 and part 2.",
                           json.dumps({"verdict": "revise", "feedback": "Say it once."}), revise]
    r = agent.handle(msg("What does Pro cost per seat monthly and when is my renewal date?", ANA))
    assert [c["step"] for c in agent.model.calls][-2:] == ["reviewer", "revise"]
    docs_in_revise = {d for d, _ in parse_documents(seen["revise_in"])}
    assert set(seen["drafts"]) <= docs_in_revise                                  # the second specialist's documents too
    assert r.citations == [seen["drafts"][1]]                                     # nothing the revised text dropped


def test_a_revision_is_told_the_tool_results_the_specialists_got():
    def revise(m, t, s):
        revise.seen = m[-1]["content"]
        return "Your renewal date is on file."

    agent = make_agent(topology="router_specialists_reviewer", tools="on")
    agent.model.replies = [json.dumps([{"area": "contract", "note": "renewal"}]),
                           {"text": "", "tool_calls": [{"name": "lookup_account", "arguments": {}}]}, "Renewal is soon.",
                           json.dumps({"verdict": "revise", "feedback": "Give the date."}), revise]
    agent.handle(msg("When is my renewal date?", ANA))
    assert "lookup_account" in revise.seen and "2027-02-28" in revise.seen        # acct-1001's renewal, from the tool result
