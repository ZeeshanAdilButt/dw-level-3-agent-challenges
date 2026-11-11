"""What every topology shares: the per-request Turn, and the answer loop (model, tool rounds, tool results back to the model)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..context import RetrievalResult
from ..prompts import format_documents
from ..tools import result_for_model, schemas
from ..types import Message

MAX_TOOL_ROUNDS = 3
MAX_CALLS_PER_ROUND = 4
TODAY = "2026-11-06"
# With tools on, a small model given many documents otherwise answers "I do not have that" instead of calling a tool:
# the reminder sits after the question, where it reads it last. Tools off: nothing is added, so labs 1 to 4 are unchanged.
TOOL_HINT = ("\n\nIf one of your tools can answer this (open slots, a quote, a booking, a claim, a lookup), "
             "call the tool now instead of answering from the documents.")


@dataclass
class Turn:
    """Everything one request accumulates. Built by the core, filled by the topology, read when the reply is made."""
    msg: Message
    tracer: object
    state: dict
    history: list
    req_hash: str
    usage: list = field(default_factory=list)
    attempted: list = field(default_factory=list)
    executed: list = field(default_factory=list)
    rule_hits: list = field(default_factory=list)
    retrievals: list = field(default_factory=list)
    precalls: list = field(default_factory=list)       # tool calls the core made before the model, shown to it as results
    handoff: dict | None = None
    pending: str | None = None
    stop_text: str | None = None                       # set when a tool step ends the turn (a clarify or a confirm)
    conflict: dict | None = None
    tool_n: int = 0
    confirmed: bool = False
    extra_cited: list = field(default_factory=list)
    clarify_tool: str | None = None                    # the action tool a clarify on this turn asked about


@dataclass
class Draft:
    text: str
    retrieval: RetrievalResult | None = None


def first_json(text: str, kind: type):
    """The first valid JSON value of `kind` (list or dict) in a model reply, or None. It scans with raw_decode from each
    opening bracket, so prose, a stray bracket or a second value around the first one does not spoil it."""
    decoder, opener = json.JSONDecoder(), "[" if kind is list else "{"
    at = text.find(opener)
    while at >= 0:
        try:
            value, _ = decoder.raw_decode(text, at)
        except ValueError:
            value = None
        if isinstance(value, kind):
            return value
        at = text.find(opener, at + 1)
    return None


def principal_block(core, turn: Turn) -> str:
    p = turn.msg.principal
    lines = [f"Signed-in user: role={p.role}, verified={'yes' if p.verified else 'no'}"
             + (f", account_id={p.account_id}" if p.verified and p.account_id else "")]
    if p.verified and p.account_id and core.pack == "juniper":
        owned = core.toolbox._patients_of(p.account_id)
        rows = [f"{x['patient_id']} {x['name']} (born {x['date_of_birth']}, CF-12 on file: {'yes' if x['cf12_complete'] else 'no'}, "
                f"upcoming: {', '.join(b['service'] + ' ' + b['date'] + ' ' + b['start'] for b in x['upcoming_bookings']) or 'none'})"
                for x in core.toolbox.fixture["patients"] if x["patient_id"] in owned]
        if rows:
            lines.append("Patients on this account: " + "; ".join(rows))
    if core.settings["tools"] == "on":
        lines.append(f"Today is {TODAY} (a Friday).")
    return "\n".join(lines)


def build_messages(core, turn: Turn, retrieval: RetrievalResult | None, system: str, feedback_block: str = "") -> list[dict]:
    marking = "marking" in core.settings["defences"]
    docs = format_documents(retrieval.delivered, core.index.titles, marking) if retrieval else ""
    messages = [{"role": "system", "content": system}]
    for u, a in turn.history:
        messages += [{"role": "user", "content": u}, {"role": "assistant", "content": a}]
    user = ((f"Documents:\n{docs}\n\n" if docs else "Documents: none were found.\n\n") + principal_block(core, turn) + "\n\n"
            + feedback_block + f"Question: {turn.msg.text}" + (TOOL_HINT if core.settings["tools"] == "on" else ""))
    messages.append({"role": "user", "content": user})
    for i, (call, tc) in enumerate(turn.precalls):
        cid = f"pre-{i}"
        messages.append({"role": "assistant", "content": "", "tool_calls": [{"id": cid, "type": "function",
                         "function": {"name": call["name"], "arguments": json.dumps(call["arguments"])}}]})
        messages.append({"role": "tool", "tool_call_id": cid, "content": result_for_model(tc)})
    return messages


def build_specialist_messages(core, turn: Turn, retrieval: RetrievalResult | None, system: str, note: str,
                              feedback_block: str = "") -> list[dict]:
    """A specialist's prompt: its area system prompt, its documents and the router's note, and nothing else. No chat
    history, no raw question and no principal block: the principal reaches tools through the core's binding only."""
    marking = "marking" in core.settings["defences"]
    docs = format_documents(retrieval.delivered, core.index.titles, marking) if retrieval else ""
    today = f"Today is {TODAY} (a Friday).\n\n" if core.settings["tools"] == "on" else ""
    user = ((f"Documents:\n{docs}\n\n" if docs else "Documents: none were found.\n\n") + today + feedback_block
            + f"{NOTE_LABEL} {note or 'Answer from your documents.'}" + (TOOL_HINT if core.settings["tools"] == "on" else ""))
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


NOTE_LABEL = "Note from the router:"


def answer_loop(core, turn: Turn, messages: list[dict], tool_names: list | None, step: str) -> str:
    """Model call, then up to three rounds of tool calls whose results go back to the model. Returns the final text."""
    tools = schemas(core.pack, tool_names) if core.settings["tools"] == "on" and tool_names != [] else None
    for rnd in range(MAX_TOOL_ROUNDS + 1):
        res = core.chat(turn, messages, tools if rnd < MAX_TOOL_ROUNDS else None, step)
        if not res.tool_calls or rnd == MAX_TOOL_ROUNDS:
            return res.text or "I could not complete that. A person can help."
        calls = res.tool_calls[:MAX_CALLS_PER_ROUND]
        messages.append({"role": "assistant", "content": res.text or "", "tool_calls": [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}} for c in calls]})
        for c in calls:
            tc = core.run_tool(turn, c, tool_names)
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": result_for_model(tc)})
            if turn.stop_text:
                return turn.stop_text
    return ""
