"""The agent core. One message in, one reply out; no channel code here (adapters live in app/adapters/).

Pipeline: idempotency reserve; rules before the model; retrieval; the access check on every item; context expansion and
assembly under one budget; the prompt; the model with tools; handoff and clarify; reply rules; defences; citations; the
eval block; the idempotent store. Every lab's change is one setting, and with every setting at its default this is a
plain RAG agent: BM25, fixed 400-word chunks, no tools, no rules, no defences.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from collections import deque
from contextlib import nullcontext
from pathlib import Path

from . import context
from .agents import run_topology
from .agents.base import Turn
from .idempotency import IdempotencyStore, request_hash
from .model import ModelClient, cost
from .prompts import fill, system_prompt, text as prompt_text
from .retrieval.index import get_index
from .rules import check_claimed_action, make_rules, parse_handoff_line
from .rules.common import AFFIRM, NEGATE, explicit_request
from .security import access
from .security.output_check import leak_check
from .settings import company_of, resolved
from .tools import ACTION_TOOLS, ToolBox, idem_key, to_dict
from .trace import Tracer
from .types import EvalBlock, Message, Reply

DOC_MARK = re.compile(r"\[([^\]]*doc-[^\]]*)\]")
DOC_ID = re.compile(r"doc-[\w\-]+")
HISTORY_TURNS = 4
CLINIC_REASONS = ("red_flag", "clinical_question", "complaint", "billing", "fee_waiver", "records", "other")
URGENCY_MAP = {"normal": "routine", "urgent": "urgent", "soon": "soon", "routine": "routine"}
LEAK_TEXT = "I can't share that."
NOTE_REMOVED = "[note removed: it quoted text the person may not see]"


class Agent:
    def __init__(self, settings: dict, pack_dir: Path, mock, model: ModelClient | None = None):
        self.settings = resolved(settings)
        self.pack_dir = Path(pack_dir)
        if company_of(self.pack_dir.name) in ("quillon", "juniper", "saltmarsh"):
            self.settings["pack"] = self.pack_dir.name
        if os.environ.get("DW_MODEL_PATH") == "stub":                  # CI and tests: never touch the network
            self.settings["model_path"] = "stub"
        self.pack = company_of(self.settings["pack"])          # rules, tools and prompts follow the company
        self.mock = mock
        self.model = model or ModelClient(self.settings)
        self.index = get_index(self.pack_dir, self.settings)         # cut and indexed once, cached
        self.toolbox = ToolBox(self.pack, self.pack_dir, mock)
        fixture = self.toolbox.fixture
        self.hard_rules = fixture.get("hard_rules", [])
        self.rules = make_rules(self.pack, fixture, self.settings)
        self.idem = IdempotencyStore()
        self._lock = threading.Lock()
        self._states: dict = {}
        self._history: dict = {}

    def set_mock(self, mock) -> None:
        """Point this agent at another mock (the harness reuses one agent across cases, one namespace each)."""
        self.mock = mock
        self.toolbox.mock = mock
        if getattr(mock, "pack", None) is None:
            mock.pack = self.pack

    # ---- small helpers ------------------------------------------------------------------------------------------
    @property
    def rules_on(self) -> bool:
        return self.settings["rules"] == "on"

    @property
    def tools_on(self) -> bool:
        return self.settings["tools"] == "on"

    @property
    def authority_on(self) -> bool:
        return self.settings["authority_rule"] == "on" or (self.rules_on and getattr(self.rules, "force_authority", False))

    def _allow_fn(self, principal):
        """The access check bound to a principal, or None when the access defence is off (the baseline leaks, by design)."""
        if "access" not in self.settings["defences"]:
            return None
        return lambda item: access.allowed(item, principal)

    def _state(self, pid: str, conv: str) -> dict:
        with self._lock:
            return self._states.setdefault((pid, conv), {})

    def span(self, turn: Turn, name: str, force: bool = False, **attrs):
        """Starter: structural spans only. Lab 8 adds a span around each step, behind trace_steps."""
        return turn.tracer.span(name, **attrs) if force else nullcontext()

    def parse_citations(self, text_: str, delivered: set) -> list:
        """Document ids from [doc-...] markers, kept only if the document was delivered to the model."""
        out = []
        for m in DOC_MARK.finditer(text_ or ""):
            for did in DOC_ID.findall(m.group(1)):
                if did in delivered and did not in out:
                    out.append(did)
        return out

    # ---- public: retrieval alone, for the harness screen --------------------------------------------------------
    def retrieve(self, query: str, principal) -> context.RetrievalResult:
        return context.retrieve(self.index, query, principal, self._effective_settings(), self._allow_fn(principal))

    def _effective_settings(self) -> dict:
        s = dict(self.settings)
        if self.authority_on:
            s["authority_rule"] = "on"
        return s

    def retrieve_turn(self, turn: Turn, area_types=None) -> context.RetrievalResult:
        principal = turn.msg.principal
        res = context.retrieve(self.index, turn.msg.text, principal, self._effective_settings(), self._allow_fn(principal), area_types,
                               span=lambda name, **a: self.span(turn, name, **a))
        turn.retrievals.append(res)
        turn.rule_hits += [f"link_refused:{t}" for t in res.refused_links]      # shows in the case record's eval block
        return res

    # ---- the model and the tools --------------------------------------------------------------------------------
    def chat(self, turn: Turn, messages: list, tools: list | None, step: str):
        res = self.model.chat(messages, tools, step, turn.tracer)
        last = turn.tracer.spans[-1] if turn.tracer.spans else None
        paid, equiv = cost(res.model, res.tokens_in, res.tokens_out)
        turn.usage.append({"model": res.model, "tokens_in": res.tokens_in, "tokens_out": res.tokens_out, "step": step,
                           "span_id": last.span_id if last is not None and last.name == "model" else None,
                           "cost_usd": paid, "hosted_equivalent_usd": equiv})
        return res

    def _own_text(self, turn: Turn) -> str:
        """What the person already holds, for the leak check. Never the message text: typing someone's email or policy
        number does not make it yours. Their own fixture records (a verified principal, or an identity proved with
        lookup_policy), the results of their successful tool calls, the arguments of an action held for their confirm
        (the confirm question repeats them), and the replies already sent to them."""
        p, state = turn.msg.principal, turn.state
        records = self.toolbox.own_records({p.account_id if p.verified else None, state.get("verified_account")})
        parts = [json.dumps(r, default=str) for r in records]
        parts += [json.dumps((e.get("receipt") or {}).get("result") or {}, default=str) for e in turn.attempted
                  if (e.get("receipt") or {}).get("ok")]
        parts += [json.dumps(e.get("arguments") or {}, default=str) for e in turn.attempted if e.get("reason") == "held for confirmation"]
        parts += [h[1] for h in turn.history]
        return "\n".join(parts)

    def _scrub_note(self, turn: Turn, note: str) -> str:
        """A handoff note that quotes text the person may not see is replaced (with the access defence on)."""
        if "access" not in self.settings["defences"] or not note:
            return note
        bad = leak_check(note, system_prompt="", principal=turn.msg.principal, index=self.index, own_text=self._own_text(turn))
        return NOTE_REMOVED if any(r.startswith("hidden-text") for r in bad) else note

    def run_tool(self, turn: Turn, call: dict, allowed_names: list | None = None, precall: bool = False):
        """Check, hold for a clarify or a confirm when the rules are on, run through the tool box, record the attempt."""
        msg, state = turn.msg, turn.state
        principal = msg.principal
        key = idem_key(principal.id, msg.conversation_id, msg.request_id, turn.req_hash, turn.tool_n)
        turn.tool_n += 1
        name = call.get("name", "")
        refusal = None
        args_in = call.get("arguments")
        if name == "hand_off" and isinstance(args_in, dict) and isinstance(args_in.get("note"), str):
            call = {**call, "arguments": {**args_in, "note": self._scrub_note(turn, args_in["note"])}}   # the model's own hand_off too
        if allowed_names is not None and name not in allowed_names and name in self.toolbox.names():
            refusal = f"tool {name} is not available to this specialist"
        tc = None
        if refusal is None and self.rules_on and name in ACTION_TOOLS:
            args, reason = self.toolbox.prepare(name, call.get("arguments") or {}, principal, state)
            if reason and reason.startswith("missing argument"):
                q = f"I need a little more to do that: {reason.split(':', 1)[1].strip()}. Could you tell me?"
                turn.stop_text, turn.pending, turn.clarify_tool = q, q, name
                refusal = "clarify: " + reason
            elif reason is None and not turn.confirmed and not precall and not self._explicit(turn, name):
                q = f"Please confirm: {self._describe_call(name, args)}. Reply yes to go ahead or no to cancel."
                state["pending_confirm"] = {"call": {"name": name, "arguments": args}}
                turn.stop_text, turn.pending = q, q
                refusal = "held for confirmation"
        with self.span(turn, "tool", tool=name):                # one span per tool call (only with trace_steps on)
            tc = self.toolbox.run(call, principal, state, key, extra_refusal=refusal, gate=self._allow_fn(principal))
        d = to_dict(tc)
        turn.attempted.append(d)
        if not tc.refused and (tc.receipt or {}).get("ok"):
            turn.executed.append(d)
        r = tc.receipt or {}
        if r.get("error") == "needs_approval" and turn.handoff is None:
            who = (r.get("result") or {}).get("approver", "the sales manager")
            turn.handoff = {"reason": "discount_over_line", "urgency": "normal",
                            "note": f"A quote with a discount above the line was refused by the quote tool. Needs approval from {who}. Request: {msg.text[:200]}"}
        if precall:
            turn.precalls.append((call, tc))
        return tc

    @staticmethod
    def _explicit(turn: Turn, name: str) -> bool:
        """Did the user ask for this action by name, or answer a clarify that this same tool asked?"""
        return explicit_request(name, turn.msg.text) or turn.state.get("clarified") == name

    @staticmethod
    def _describe_call(name: str, args: dict) -> str:
        bits = ", ".join(f"{k}={v}" for k, v in args.items() if v not in (None, ""))
        return f"{name.replace('_', ' ')} ({bits})"

    @staticmethod
    def _describe_result(tc) -> str:
        if tc.refused:
            return f"I couldn't do that: {tc.reason}."
        r = tc.receipt or {}
        if not r.get("ok"):
            return f"The system did not accept that: {r.get('message') or r.get('error')}."
        res = r.get("result") or {}
        if tc.name == "book_demo":
            return f"Your demo is booked for {res.get('start_utc')} (slot {res.get('slot_id')}). Receipt {r.get('receipt_id')}."
        if tc.name == "book_appointment":
            return f"Booked {res.get('service')} on {res.get('date')} at {res.get('start')} for {res.get('patient_id')}. Receipt {r.get('receipt_id')}."
        if tc.name == "open_claim":
            return f"Claim {res.get('claim_id')} is open with status {res.get('status')}. Opening a claim does not decide cover. Receipt {r.get('receipt_id')}."
        if tc.name == "create_quote":
            return f"Quote {res.get('quote_id')}: {res.get('seats')} seats, {res.get('term')}, net total ${res.get('net_total_usd')}. Receipt {r.get('receipt_id')}."
        return f"Done. Receipt {r.get('receipt_id')}."

    # ---- the company classifier (also callable on its own: the diagnostic set) -----------------------------------
    def classify(self, text_: str, turn: Turn | None = None) -> str:
        own = turn is None
        if own:
            turn = Turn(msg=None, tracer=Tracer("classify"), state={}, history=[], req_hash="")
        cats = {"juniper": ("red_flag", "medicine_advice", "diagnosis_request"), "quillon": ("discount_pressure", "agree_trap", "price_commitment"), "saltmarsh": ("payout_demand",)}.get(self.pack, ())
        name = "classifier.txt" if self.pack == "juniper" else f"classifier_{self.pack}.txt"
        messages = [{"role": "system", "content": prompt_text(name)}, {"role": "user", "content": f"Question: {text_}"}]
        res = self.chat(turn, messages, None, "classifier")
        m = re.search(r'"category"\s*:\s*"(\w+)"', res.text)
        cat = m.group(1) if m else next((c for c in cats if c in res.text), "none")
        return cat if cat in cats + ("none",) else "none"

    # ---- one request --------------------------------------------------------------------------------------------
    # SHIPPED STUB in the starter: a core that answers "I don't know yet" with no citation.
    def handle(self, msg: Message) -> Reply:
        """Starter core: answers "I don't know yet" with no citation. Lab 1 part 2 replaces this."""
        return self._plain(msg, "I don't know yet.")

    def _plain(self, msg: Message, text_: str, in_progress: bool = False) -> Reply:
        return Reply(text=text_, citations=[], actions=[], pending=None, handoff=None, usage=[], cost_usd=0.0, latency_ms=0.0,
                     trace_id="tr-" + uuid.uuid4().hex[:12], eval=EvalBlock(raw_reply=text_), in_progress=in_progress)

    # ---- the reply ---------------------------------------------------------------------------------------------------
    def _reply(self, turn: Turn, text_: str, latency_ms: float) -> Reply:
        delivered_docs = []
        for r in turn.retrievals:
            delivered_docs += r.delivered_doc_ids
        delivered_set = set(delivered_docs)
        citations = self.parse_citations(text_, delivered_set)
        for c in turn.extra_cited:
            if c in delivered_set and c not in citations:
                citations.append(c)

        def union(attr):
            return list(dict.fromkeys(i for r in turn.retrievals for i in getattr(r, attr)))

        ev = EvalBlock(raw_reply=text_, ranked_hit_ids=union("ranked_ids"), expanded_evidence_ids=union("expanded_ids"),
                       delivered_evidence_ids=union("delivered_ids"), delivered_doc_ids=list(dict.fromkeys(delivered_docs)),
                       delivered_text="\n\n".join(r.delivered_text for r in turn.retrievals if r.delivered_text),
                       delivered_tokens=sum(r.delivered_tokens for r in turn.retrievals), truncated=any(r.truncated for r in turn.retrievals),
                       attempted_tool_calls=turn.attempted, executed_actions=turn.executed, pending=turn.pending, handoff=turn.handoff,
                       usage=turn.usage, spans=turn.tracer.export(), rule_hits=turn.rule_hits)
        return Reply(text=text_, citations=citations, actions=turn.executed, pending=turn.pending, handoff=turn.handoff,
                     usage=turn.usage, cost_usd=sum(u["cost_usd"] for u in turn.usage), latency_ms=latency_ms,
                     trace_id="tr-" + uuid.uuid4().hex[:12], eval=ev)
