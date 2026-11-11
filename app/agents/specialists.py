"""Specialists: an answer loop restricted to one area's documents and tools. The single agent is the same loop with no area."""
from __future__ import annotations

from ..prompts import fill, system_prompt, text
from .base import Draft, Turn, answer_loop, build_messages, build_specialist_messages

# area -> description (the router reads it), document types (the specialist sees only these; "*" = every type nobody lists), tools
AREAS = {
    "quillon": {
        "sales": {"description": "pricing plans seats price billing discount quote demo product features integrations customers case studies brochure release notes",
                  "types": ["pricing", "brochure", "product", "case-study", "faq", "integration", "release-note"], "tools": ["create_quote", "book_demo"]},
        "contract": {"description": "contract clauses terms service levels uptime sla liability termination data protection security support account renewal policy",
                     "types": ["clause", "contract", "policy", "security", "support", "*"], "tools": ["lookup_account"]},
    },
    "juniper": {
        "booking": {"description": "book appointment slot service preparation rules fasting blood test hours opening times cancel reschedule reminders prices fees guide team",
                    "types": ["support", "policy", "product", "guide", "team", "form", "pricing", "community", "newsletter", "brochure", "release-note"],
                    "tools": ["check_slots", "book_appointment", "hand_off"]},
        "insurance": {"description": "insurer insurance direct billing excess claims invoice receipt privacy faq",
                      "types": ["insurer", "faq", "*"], "tools": ["hand_off"]},
    },
    "saltmarsh": {
        "cover": {"description": "cover policy wording excess exclusions riders products endorsements flood storm theft limits renewal premium",
                  "types": ["clause", "endorsement", "product", "brochure", "faq", "company", "case-study"], "tools": ["lookup_policy"]},
        "claims": {"description": "claim claims status open report loss settlement assess documents support complaints process",
                   "types": ["claims", "support", "release-note", "*"], "tools": ["lookup_policy", "check_claim", "open_claim"]},
    },
}


def area_types(core, area: str) -> set:
    listed = {t for a in AREAS[core.pack].values() for t in a["types"] if t != "*"}
    mine = set(AREAS[core.pack][area]["types"])
    if "*" in mine:
        mine |= {d.meta.get("type") for d in core.index.docs.values()} - listed
    return mine - {"*"}


def area_system(core, area: str | None, note: str = "") -> str:
    base = system_prompt(core.pack, core.settings, core.hard_rules)
    if area:
        spec = AREAS[core.pack][area]
        base += "\n\n" + fill(text("specialist.txt"), area=area, description=spec["description"], note=note or "Answer the customer's question.")
    return base


def run_specialist(core, turn: Turn, area: str | None = None, note: str = "", feedback_block: str = "") -> Draft:
    """Starter: the single agent path only (no area). Lab 6 part 1 adds the specialist's own documents and tools."""
    if area:
        raise NotImplementedError("YOUR TURN: lab 6 part 1, specialists")
    retrieval = core.retrieve_turn(turn)
    messages = build_messages(core, turn, retrieval, area_system(core, None, note), feedback_block)
    return Draft(answer_loop(core, turn, messages, None, "answer"), retrieval)
