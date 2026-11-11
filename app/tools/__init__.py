"""Tools: the three per company, with argument validation and ownership bound to the principal.

The model asks; the core checks. A call is refused (and recorded with the reason) if the tool is unknown, an argument is
missing, unknown or of the wrong type, the principal is not allowed that tool, or the call names an account, patient or
policy the principal does not own. The principal always comes from the core, never from the model's arguments.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from ..types import ToolCall

PLANS = ["PLN-STR-10", "PLN-TEAM-25", "PLN-PRO-50", "PLN-ENT-200"]
SERVICES = ["gp_consult", "gp_extended", "child_check", "vaccination", "travel_consult", "blood_fasting", "blood_standard",
            "glucose_tolerance", "physio_assessment", "physio_followup", "cervical_screening", "womens_health",
            "minor_procedure", "procedure_precheck", "telehealth", "registration"]
CLAIM_TYPES = ["escape_of_water", "theft", "storm", "flood", "fire", "accidental_damage", "subsidence", "motor_accident",
               "motor_theft", "windscreen", "home_emergency", "legal_expenses"]

# name -> (description, {argument: schema}, required arguments)
SPECS = {
    "quillon": {
        "lookup_account": ("Look up the signed-in customer's own account (plan, seats, renewal date). Give account_id or email.",
                           {"account_id": {"type": "string"}, "email": {"type": "string"}}, []),
        "create_quote": ("Create a price quote for the signed-in customer's own account. The only source for a quote total.",
                         {"account_id": {"type": "string"}, "plan": {"type": "string", "enum": PLANS}, "seats": {"type": "integer"},
                          "term": {"type": "string", "enum": ["monthly", "annual"]}, "discount_pct": {"type": "number"}},
                         ["plan", "seats", "term"]),
        "book_demo": ("Book one available demo slot for a prospect's email.",
                      {"email": {"type": "string"}, "slot_id": {"type": "string"}, "timezone": {"type": "string"}},
                      ["email", "slot_id", "timezone"]),
    },
    "juniper": {
        "check_slots": ("List open slots for one service in a date range (at most 28 days ahead). Read-only.",
                        {"service": {"type": "string", "enum": SERVICES}, "date_from": {"type": "string"}, "date_to": {"type": "string"}},
                        ["service"]),
        "book_appointment": ("Book one slot for one of the signed-in person's own patients.",
                             {"patient_id": {"type": "string"}, "slot_id": {"type": "string"}, "service": {"type": "string", "enum": SERVICES}},
                             ["slot_id", "service"]),
        "hand_off": ("Pass the person to staff with a note. Red flags use reason red_flag and urgency urgent.",
                     {"reason": {"type": "string", "enum": ["red_flag", "clinical_question", "complaint", "billing", "fee_waiver", "records", "other"]},
                      "urgency": {"type": "string", "enum": ["urgent", "soon", "routine"]}, "note": {"type": "string"}},
                     ["reason", "urgency"]),
    },
    "saltmarsh": {
        "lookup_policy": ("Verify identity (policy number plus date of birth, as YYYY-MM-DD) and look up the policy.",
                          {"policy_number": {"type": "string"}, "date_of_birth": {"type": "string"}}, ["policy_number", "date_of_birth"]),
        "check_claim": ("Status and history of one of the verified person's own claims.", {"claim_id": {"type": "string"}}, ["claim_id"]),
        "open_claim": ("Open a claim (status received) on the verified person's own policy. Does not decide cover.",
                       {"policy_number": {"type": "string"}, "date_of_loss": {"type": "string"}, "description": {"type": "string"},
                        "claim_type": {"type": "string", "enum": CLAIM_TYPES}}, ["policy_number", "date_of_loss", "description", "claim_type"]),
    },
}
STATE_CHANGING = {"create_quote", "book_demo", "book_appointment", "hand_off", "open_claim"}
ACTION_TOOLS = {"create_quote", "book_demo", "book_appointment", "open_claim"}   # held for confirmation when the user did not ask


def schemas(pack: str, names: list | None = None) -> list[dict]:
    out = []
    for name, (desc, props, req) in SPECS[pack].items():
        if names is not None and name not in names:
            continue
        out.append({"type": "function", "function": {"name": name, "description": desc,
                                                     "parameters": {"type": "object", "properties": props, "required": req}}})
    return out


def idem_key(principal_id: str, conversation_id: str, request_id: str, req_hash: str, n: int) -> str:
    return hashlib.sha256(f"{principal_id}|{conversation_id}|{request_id}|{req_hash}|{n}".encode()).hexdigest()[:32]


def validate(pack: str, name: str, args: dict):
    """(cleaned arguments, None) or (None, reason)."""
    if name not in SPECS[pack]:
        return None, f"unknown tool {name!r}"
    _, props, required = SPECS[pack][name]
    if "_invalid" in args:
        return None, "arguments are not valid JSON"
    extra = [k for k in args if k not in props]
    if extra:
        return None, f"unknown argument {extra[0]!r} (who is calling comes from the system, not from arguments)"
    out = {}
    for k, v in args.items():
        t = props[k]["type"]
        if v is None:
            continue
        if t == "string":
            if not isinstance(v, str):
                return None, f"{k} must be a string"
            v = v.strip()
        elif t == "integer":
            if isinstance(v, bool) or not isinstance(v, (int, float, str)):
                return None, f"{k} must be a whole number"
            try:
                fv = float(v)
            except ValueError:
                return None, f"{k} must be a whole number"
            if fv != int(fv):
                return None, f"{k} must be a whole number"
            v = int(fv)
        elif t == "number":
            if isinstance(v, bool) or not isinstance(v, (int, float, str)):
                return None, f"{k} must be a number"
            try:
                v = float(v) if not isinstance(v, (int, float)) else v
            except ValueError:
                return None, f"{k} must be a number"
        if "enum" in props[k] and v not in props[k]["enum"]:
            return None, f"{k} must be one of {', '.join(props[k]['enum'])}"
        out[k] = v
    missing = [k for k in required if out.get(k) in (None, "")]
    if missing:
        return None, f"missing argument: {', '.join(missing)}"
    return out, None


class ToolBox:
    def __init__(self, pack: str, pack_dir: Path, mock, gate=None):
        self.pack, self.mock = pack, mock
        self.fixture = json.loads((Path(pack_dir) / "tools" / "fixture.json").read_text(encoding="utf-8"))
        self.gate = gate                       # allowed(item) bound to the principal, or None
        if getattr(mock, "pack", None) is None:
            mock.pack = pack

    def names(self) -> list[str]:
        return list(SPECS[self.pack])

    # -- ownership tables, read from the fixture --------------------------------------------------------------------
    def _account(self, account_id):
        return next((a for a in self.fixture.get("accounts", []) if a["account_id"] == account_id), None)

    def _patients_of(self, account_id) -> list[str]:
        acc = self._account(account_id)
        return list(acc.get("owns_patient_ids", [])) if acc else []

    def _policy(self, number):
        return next((p for p in self.fixture.get("policyholders", []) if p["policy_number"] == number), None)

    def _claim(self, claim_id):
        return next((c for c in self.fixture.get("claims", []) if c["claim_id"] == claim_id), None)

    def own_records(self, account_ids) -> list[dict]:
        """Every fixture record that belongs to these accounts (the account, its patients, policies and claims)."""
        ids = {a for a in account_ids if a}
        out = []
        for key, rows in self.fixture.items():
            if key == "principals" or not isinstance(rows, list):
                continue
            out += [r for r in rows if isinstance(r, dict) and (r.get("account_id") in ids or r.get("owner_account_id") in ids)]
        return out

    # -- binding ------------------------------------------------------------------------------------------------------
    def bind(self, name: str, args: dict, principal, state: dict):
        """Fill what comes from the principal and refuse what the principal does not own. (bound arguments, None) or (None, reason)."""
        raise NotImplementedError("YOUR TURN: lab 5 part 1, principal binding and ownership")

    def prepare(self, name: str, raw: dict, principal, state: dict):
        """Validate and bind without calling anything. (final arguments, None) or (None, reason)."""
        args, reason = validate(self.pack, name, dict(raw or {}))
        if reason is None:
            args, reason = self.bind(name, args, principal, state)
        return args, reason

    def run(self, call: dict, principal, state: dict, key: str, extra_refusal: str | None = None, gate=None) -> ToolCall:
        """Validate, bind, call the mock. Always returns a ToolCall; a refused one never reaches the mock."""
        name, raw = call.get("name", ""), dict(call.get("arguments") or {})
        if extra_refusal:
            return ToolCall(name, raw, refused=True, reason=extra_refusal, idempotency_key=key)
        args, reason = self.prepare(name, raw, principal, state)
        if reason is not None:
            return ToolCall(name, raw, refused=True, reason=reason, idempotency_key=key)
        receipt = self.mock.call(name, args, principal, key)
        gate = gate or self.gate
        if receipt.get("ok") and gate is not None:
            res = receipt.get("result") or {}
            signed_in = principal.account_id if principal.verified else None
            # lookup_policy is the identity proof only for someone not signed in; a signed-in holder's result must be their own
            proof = res.get("account_id") if name == "lookup_policy" and not signed_in else state.get("verified_account")
            item = {"kind": "tool_result", "account_id": res.get("account_id") or res.get("owner_account_id"), "verified_account": proof}
            if not gate(item):
                return ToolCall(name, args, refused=True, reason="access: the result belongs to someone else", idempotency_key=key)
        if name == "lookup_policy" and receipt.get("ok"):
            state["verified_account"] = (receipt.get("result") or {}).get("account_id")
        return ToolCall(name, args, refused=False, receipt=receipt, idempotency_key=key)


def result_for_model(tc: ToolCall) -> str:
    """What the model reads back after a call."""
    if tc.refused:
        return json.dumps({"ok": False, "refused": True, "reason": tc.reason})
    r = tc.receipt or {}
    if r.get("ok"):
        return json.dumps({"ok": True, "result": r.get("result")}, default=str)
    return json.dumps({"ok": False, "error": r.get("error"), "message": r.get("message"), "result": r.get("result")}, default=str)


def to_dict(tc: ToolCall) -> dict:
    return asdict(tc)
