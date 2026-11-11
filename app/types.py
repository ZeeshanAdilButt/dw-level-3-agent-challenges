"""Shared types for the agent core, the adapters and the harness. Everything else builds on these.

The contract is in the course notes, section 2 and
INTERFACES.md in this repository.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Principal:
    id: str                      # fixture principal id, for example "acct-1004-owner" or "prospect-02"
    role: str                    # customer | staff | prospect | patient | policyholder
    verified: bool               # set by the adapter, never by the message
    account_id: Optional[str]    # the account, patient or policy this principal owns, if any


@dataclass(frozen=True)
class Message:
    request_id: str
    conversation_id: str
    principal: Principal
    text: str


@dataclass
class Span:
    span_id: str
    parent_id: Optional[str]
    name: str                    # retrieve | expand | assemble | model | tool | rules | classifier | router | specialist | reviewer
    start_ms: float
    end_ms: float
    model: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    attrs: dict = field(default_factory=dict)


@dataclass
class ToolCall:
    name: str
    arguments: dict
    refused: bool = False
    reason: Optional[str] = None             # why the core refused it, if refused
    receipt: Optional[dict] = None           # the mock's receipt, if it ran
    idempotency_key: Optional[str] = None


@dataclass
class Handoff:
    reason: str
    note: str
    urgency: str = "normal"                  # normal | urgent


@dataclass
class EvalBlock:
    raw_reply: str = ""
    ranked_hit_ids: list = field(default_factory=list)        # chunk ids, rank order
    expanded_evidence_ids: list = field(default_factory=list)
    delivered_evidence_ids: list = field(default_factory=list)  # chunk ids actually given to the model
    delivered_doc_ids: list = field(default_factory=list)
    delivered_text: str = ""                                    # kept in cases.jsonl for context fact recall
    delivered_tokens: int = 0
    truncated: bool = False
    attempted_tool_calls: list = field(default_factory=list)   # ToolCall as dicts, refused ones included
    executed_actions: list = field(default_factory=list)       # ToolCall as dicts that ran, with receipts
    pending: Optional[str] = None
    handoff: Optional[dict] = None
    usage: list = field(default_factory=list)                  # one dict per model call: model, tokens_in, tokens_out
    spans: list = field(default_factory=list)                  # Span as dicts
    rule_hits: list = field(default_factory=list)              # which hard rules or classifiers fired


@dataclass
class Reply:
    text: str
    citations: list                          # document ids
    actions: list                            # executed actions (ToolCall dicts)
    pending: Optional[str]
    handoff: Optional[dict]
    usage: list
    cost_usd: float
    latency_ms: float
    trace_id: str
    eval: EvalBlock = field(default_factory=EvalBlock)
    in_progress: bool = False                # a concurrent duplicate request is still running

    def to_dict(self, with_eval: bool = False) -> dict:
        d = asdict(self)
        if not with_eval:
            d.pop("eval", None)
        return d


def principal_id(d: dict[str, Any]) -> str:
    """The id of a principal given as a dict: its own id, else "<account>-owner", else "<role>-anon". The harness and the
    chat adapter's test header both use this, so one principal has one id on both paths."""
    if d.get("id"):
        return str(d["id"])
    if d.get("account_id"):
        return f"{d['account_id']}-owner"
    return f"{d.get('role', 'prospect')}-anon"


def principal_from_dict(d: dict[str, Any]) -> Principal:
    return Principal(id=d["id"], role=d.get("role", "customer"), verified=bool(d.get("verified", False)),
                     account_id=d.get("account_id"))
