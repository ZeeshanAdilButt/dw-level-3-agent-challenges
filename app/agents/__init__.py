"""Topologies: single, router_specialists, router_specialists_reviewer. `run_topology` returns the draft text for the core to check."""
from __future__ import annotations

import json

from ..context import RetrievalResult
from ..prompts import text
from .base import Turn, build_specialist_messages
from .reviewer import review
from .router import route
from .specialists import area_system, run_specialist


def _cited(core, text_: str, retrievals) -> list:
    return core.parse_citations(text_, {d for r in retrievals for d in r.delivered_doc_ids})


def _all_delivered(retrievals) -> RetrievalResult:
    """Every chunk any specialist was given, once, in the order delivered: what a revision may use."""
    out, seen = RetrievalResult(), set()
    for r in retrievals:
        for c in r.delivered:
            if c.chunk_id not in seen:
                seen.add(c.chunk_id)
                out.delivered.append(c)
    return out


def _tool_results(turn: Turn) -> str:
    """The tool calls the specialists made and what came back, so a revision keeps them (it calls no tools itself)."""
    lines = []
    for a in turn.attempted:
        r = a.get("receipt") or {}
        out = {"refused": True, "reason": a.get("reason")} if a.get("refused") else {"ok": r.get("ok"), "result": r.get("result"), "error": r.get("error")}
        lines.append(f"- {a.get('name')}: {json.dumps(out, default=str)}")
    return ("Tool results already received (do not call again):\n" + "\n".join(lines) + "\n") if lines else ""


def run_topology(core, turn: Turn) -> str:
    topology = core.settings["topology"]
    if topology == "single":
        return run_specialist(core, turn, None).text

    picks = route(core, turn)
    drafts = []
    for pick in picks:
        with core.span(turn, "specialist", force=True, area=pick["area"]):
            drafts.append(run_specialist(core, turn, pick["area"], pick["note"]))
        if turn.conflict or turn.stop_text:
            break
    if turn.conflict:
        return ""
    for d in drafts:
        turn.extra_cited += _cited(core, d.text, [d.retrieval])
    if len(drafts) == 1 or turn.stop_text:
        final = drafts[-1].text
    else:
        parts = "\n".join(f"PART {i + 1}: {d.text}" for i, d in enumerate(drafts))
        messages = [{"role": "system", "content": text("merge.txt")}, {"role": "user", "content": f"{parts}\n\nQuestion: {turn.msg.text}"}]
        final = core.chat(turn, messages, None, "merge").text

    if topology == "router_specialists_reviewer" and not turn.stop_text:
        delivered = list(dict.fromkeys(d for r in turn.retrievals for d in r.delivered_doc_ids))
        verdict = review(core, turn, final, _cited(core, final, turn.retrievals), delivered)
        if verdict["verdict"] == "revise":                      # one revision, never more
            block = f"REVISED. Reviewer feedback: {verdict['feedback']}\nYour earlier draft: {final}\n" + _tool_results(turn)
            area, note = (picks[0]["area"], picks[0]["note"]) if len(drafts) == 1 else (None, " ".join(p["note"] for p in picks))
            messages = build_specialist_messages(core, turn, _all_delivered(turn.retrievals), area_system(core, area, picks[0]["note"] if area else ""),
                                                 note, block)          # a team member: the notes, never the chat or the principal
            final = core.chat(turn, messages, None, "revise").text
            turn.extra_cited = _cited(core, final, turn.retrievals)  # the revised text alone decides its citations
    return final
