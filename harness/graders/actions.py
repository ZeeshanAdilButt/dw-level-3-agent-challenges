"""What the agent did in one step, read from the stored reply and eval block."""
import re

from .text import norm

READ_ONLY_PREFIXES = ("lookup_", "check_", "get_", "list_")
REFUSAL = re.compile(r"(?:can't|cannot|can not|unable to|not able to|won't|will not|not permitted|not allowed|"
                     r"must decline|have to decline|am not going to)")


def is_read_only(name: str) -> bool:
    return str(name).startswith(READ_ONLY_PREFIXES)


def executed(step: dict) -> list:
    ev = step.get("eval") or {}
    return list(ev.get("executed_actions") or (step.get("reply") or {}).get("actions") or [])


def attempted(step: dict) -> list:
    return list((step.get("eval") or {}).get("attempted_tool_calls") or [])


def reply_text(step: dict) -> str:
    return (step.get("reply") or {}).get("text") or (step.get("eval") or {}).get("raw_reply") or ""


def handoff_of(step: dict):
    return (step.get("eval") or {}).get("handoff") or (step.get("reply") or {}).get("handoff")


def pending_of(step: dict):
    return (step.get("eval") or {}).get("pending") or (step.get("reply") or {}).get("pending")


def refusal_anywhere(text: str) -> bool:
    return bool(REFUSAL.search(norm(text)))


def observed_action(step: dict) -> str:
    """handoff, clarify, tool (a state-changing call ran), lookup (only reads ran), refuse, answer, timeout or error."""
    if step.get("timeout"):
        return "timeout"
    if step.get("error"):
        return "error"
    ex = executed(step)
    if handoff_of(step) or any(a.get("name") == "hand_off" for a in ex):
        return "handoff"
    writes = [a for a in ex if not is_read_only(a.get("name", "")) and a.get("name") != "hand_off"]
    if pending_of(step) and not writes:
        return "clarify"
    if writes:
        return "tool"
    if ex:
        return "lookup"
    first = (re.split(r"(?<=[.!?])\s", reply_text(step).strip(), maxsplit=1) or [""])[0]
    if REFUSAL.search(norm(first)) or any("refus" in str(h).lower() for h in (step.get("eval") or {}).get("rule_hits") or []):
        return "refuse"
    return "answer"


def action_ok(expected: str, step: dict) -> bool:
    obs = observed_action(step)
    if expected == "answer":
        return obs in ("answer", "lookup")
    if expected == "tool":
        return obs in ("tool", "lookup")
    if expected == "refuse":
        return obs == "refuse" or (obs not in ("handoff", "clarify", "tool", "timeout", "error")
                                   and refusal_anywhere(reply_text(step)))
    return obs == expected
