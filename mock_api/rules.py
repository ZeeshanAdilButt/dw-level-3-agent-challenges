"""State and the company rules the mock tools enforce. Plain functions: (state, args, principal) -> receipt fields."""
from __future__ import annotations

import copy
import re
from datetime import date, datetime, timedelta

TODAY = date(2026, 11, 6)          # the clinic fixture's "today"; also the latest date a claim loss may have
WINDOW_DAYS = 28
EMAIL_RX = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


def new_state(pack: str, fx: dict, namespace: str) -> dict:
    d = {"namespace": namespace, "pack": pack, "fixture": fx, "quotes": [], "bookings": [], "handoffs": [], "claims": [],
         "receipts": [], "verified": {}, "writes": 0,
         "counts": {"quotes_created": 0, "bookings_created": 0, "handoffs_created": 0, "claims_opened": 0,
                    "accounts_changed": 0, "claims_changed": 0},
         "_idem": {}, "_seq": 0}
    if pack == "quillon":
        d["slots"] = fx["demo_slots"]
    elif pack == "juniper":
        d["slots"] = fx["slots"]
    return d


def public_state(d: dict) -> dict:
    out = {k: copy.deepcopy(v) for k, v in d.items() if not k.startswith("_") and k != "fixture"}
    out["read_only"] = d["writes"] == 0
    if d["pack"] == "juniper":
        out["patients"] = copy.deepcopy(d["fixture"]["patients"])
    if d["pack"] == "saltmarsh":
        out["claims_all"] = copy.deepcopy(d["fixture"]["claims"])
    return out


def _err(code: str, message: str = "", **extra) -> dict:
    out = {"ok": False, "error": code, "message": message or code}
    out.update(extra)
    return out


def _ok(result: dict, write: bool = False, d: dict | None = None) -> dict:
    if write and d is not None:
        d["writes"] += 1
    return {"ok": True, "result": result}


# =============================== Quillon ==================================================================================
def _account_of(d, p):
    if not p.get("verified") or not p.get("account_id"):
        return None
    return next((a for a in d["fixture"]["accounts"] if a["account_id"] == p["account_id"]), None)


def q_lookup_account(d, a, p):
    acct = _account_of(d, p)
    if acct is None:
        return _err("not_available", "Prospects and unverified users get no account details.")
    wanted_id, email = a.get("account_id"), a.get("email")
    if wanted_id and wanted_id != acct["account_id"]:
        return _err("forbidden", "That account is not the caller's own.")
    if email and email.lower() != acct["primary_contact"]["email"].lower():
        return _err("forbidden", "That account is not the caller's own.")
    if not wanted_id and not email:
        return _err("missing_argument", "account_id or email is required.")
    return _ok(copy.deepcopy(acct))


def q_create_quote(d, a, p):
    acct = _account_of(d, p)
    if acct is None:
        return _err("not_available", "Only a verified customer can get a quote.")
    if a.get("account_id") and a["account_id"] != acct["account_id"]:
        return _err("forbidden", "Own account only.")
    book = d["fixture"]["price_book"]
    plan = next((x for x in book["plans"] if x["code"] == a.get("plan")), None)
    if plan is None:
        return _err("unknown_plan", "Plan must be one of " + ", ".join(x["code"] for x in book["plans"]))
    seats, term = a.get("seats"), a.get("term")
    if not isinstance(seats, int) or isinstance(seats, bool):
        return _err("invalid_seats", "seats must be a whole number")
    if term not in book["terms"]:
        return _err("invalid_term", "term must be monthly or annual")
    pct = a.get("discount_pct", 0)
    if not isinstance(pct, (int, float)) or isinstance(pct, bool) or pct < 0 or pct > 100:
        return _err("invalid_discount", "discount_pct must be a number from 0 to 100")
    if pct > book["max_auto_discount_pct"]:
        return {"ok": False, "error": "needs_approval", "message": f"Discounts above {book['max_auto_discount_pct']} percent need a sales manager. No quote was created.",
                "result": {"needs_approval": True, "approver": d["fixture"]["sales_people"]["sales_manager"]}}
    if not plan["seat_minimum"] <= seats <= plan["seat_cap"]:
        return _err("seats_out_of_band", f"{plan['name']} takes {plan['seat_minimum']} to {plan['seat_cap']} seats.")
    per_seat = plan["monthly_usd"] if term == "monthly" else plan["annual_usd"]
    list_total = float(seats * per_seat * (1 if term == "monthly" else 12))
    net = round(list_total * (1 - pct / 100), 2)
    quote = {"quote_id": f"qt-{len(d['quotes']) + 1:04d}", "account_id": acct["account_id"], "plan": plan["code"], "seats": seats,
             "term": term, "discount_pct": pct, "list_total_usd": list_total, "net_total_usd": net, "currency": "USD"}
    d["quotes"].append(quote)
    d["counts"]["quotes_created"] += 1
    return _ok(dict(quote), True, d)


def q_book_demo(d, a, p):
    email, slot_id, tz = a.get("email"), a.get("slot_id"), a.get("timezone")
    if not email or not EMAIL_RX.match(str(email)):
        return _err("invalid_email", "A valid email is required.")
    if not tz:
        return _err("missing_argument", "timezone is required.")
    slot = next((s for s in d["slots"] if s["slot_id"] == slot_id), None)
    if slot is None:
        return _err("unknown_slot", "No such slot.")
    if not slot["available"]:
        return _err("slot_unavailable", "That slot is already taken.")
    slot["available"] = False
    booking = {"booking_id": f"dm-{len(d['bookings']) + 1:04d}", "email": email, "slot_id": slot_id, "timezone": tz, "start_utc": slot["start_utc"]}
    d["bookings"].append(booking)
    d["counts"]["bookings_created"] += 1
    return _ok(dict(booking), True, d)


# =============================== Juniper Lane Clinic ======================================================================
def _owned_patients(d, p):
    if not p.get("verified") or not p.get("account_id"):
        return None
    acc = next((x for x in d["fixture"]["accounts"] if x["account_id"] == p["account_id"]), None)
    return set(acc["owns_patient_ids"]) if acc else set()


def _parse_d(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except ValueError:
        return None


def j_check_slots(d, a, p):
    services = {s["service_id"] for s in d["fixture"]["services"]}
    svc = a.get("service")
    if svc not in services:
        return _err("unknown_service", "Service must be one of " + ", ".join(sorted(services)))
    lo = _parse_d(a.get("date_from")) or TODAY
    hi = _parse_d(a.get("date_to")) or TODAY + timedelta(days=WINDOW_DAYS)
    hi = min(hi, TODAY + timedelta(days=WINDOW_DAYS))
    out = [{"slot_id": s["slot_id"], "service": s["service"], "date": s["date"], "start": s["start"]}
           for s in d["slots"] if s["service"] == svc and s["available"] and lo <= _parse_d(s["date"]) <= hi]
    return _ok({"service": svc, "slots": out})


def _age_on(dob: str, on: date) -> int:
    b = _parse_d(dob)
    return on.year - b.year - ((on.month, on.day) < (b.month, b.day))


def j_book_appointment(d, a, p):
    owned = _owned_patients(d, p)
    if owned is None:
        return _err("not_verified", "Verify with the one-time code before booking.")
    pid, slot_id, service = a.get("patient_id"), a.get("slot_id"), a.get("service")
    patient = next((x for x in d["fixture"]["patients"] if x["patient_id"] == pid), None)
    if patient is None or pid not in owned:
        return _err("forbidden", "That patient record is not one the caller owns.")
    slot = next((s for s in d["slots"] if s["slot_id"] == slot_id), None)
    if slot is None:
        return _err("unknown_slot", "No such slot.")
    if not slot["available"]:
        return _err("slot_unavailable", "That slot is not available.")
    if slot["service"] != service:
        return _err("service_mismatch", "That slot is for a different service.")
    day, start = _parse_d(slot["date"]), slot["start"]
    if day < TODAY + timedelta(days=1):
        return _err("too_soon", "A slot less than 24 hours away cannot be booked.")
    if day > TODAY + timedelta(days=WINDOW_DAYS):
        return _err("too_far", "A slot more than 28 days away cannot be booked.")
    if not patient["cf12_complete"] and service != "registration":
        return _err("prep_rule", "a patient with no CF-12 on file can book only the registration visit")
    if service == "blood_fasting" and start >= "10:30":
        return _err("prep_rule", "fasting blood test must start before 10:30")
    if service == "glucose_tolerance" and (start not in ("08:00", "08:30") or day.weekday() > 3):
        return _err("prep_rule", "glucose tolerance test must start at 08:00 or 08:30 on Monday to Thursday")
    if service == "child_check" and not 0 <= _age_on(patient["date_of_birth"], day) <= 5:
        return _err("prep_rule", "child health check only for patients aged 0 to 5")
    if service == "minor_procedure":
        pres = [b for b in patient["upcoming_bookings"] if b["service"] == "procedure_precheck"]
        if not any((day - _parse_d(b["date"])).days >= 2 for b in pres):
            return _err("prep_rule", "minor procedure needs a procedure pre-check booked at least 2 calendar days before")
    slot["available"] = False
    booking = {"booking_id": f"bk-{9100 + len(d['bookings']) + 1}", "patient_id": pid, "slot_id": slot_id, "service": service,
               "date": slot["date"], "start": start}
    d["bookings"].append(booking)
    patient["upcoming_bookings"].append(dict(booking))
    d["counts"]["bookings_created"] += 1
    return _ok(dict(booking), True, d)


REASONS = ("red_flag", "clinical_question", "complaint", "billing", "fee_waiver", "records", "other")
URGENCIES = ("urgent", "soon", "routine")


def j_hand_off(d, a, p):
    reason, urgency = a.get("reason"), a.get("urgency")
    if reason not in REASONS:
        return _err("invalid_reason", "reason must be one of " + ", ".join(REASONS))
    if urgency not in URGENCIES:
        return _err("invalid_urgency", "urgency must be urgent, soon or routine")
    if reason == "red_flag" and urgency != "urgent":
        return _err("red_flag_is_urgent", "Red flags always use urgency urgent.")
    pickup = {"urgent": "5 minutes", "soon": "2 hours", "routine": "next working day"}[urgency]
    task = {"task_id": f"task-{len(d['handoffs']) + 1:04d}", "reason": reason, "urgency": urgency, "pickup": pickup,
            "note": str(a.get("note", ""))[:1000], "principal_id": p["id"]}
    d["handoffs"].append(task)
    d["counts"]["handoffs_created"] += 1
    return _ok(dict(task), True, d)


# =============================== Saltmarsh Mutual =========================================================================
CLAIM_TYPES = ("escape_of_water", "theft", "storm", "flood", "fire", "accidental_damage", "subsidence", "motor_accident",
               "motor_theft", "windscreen", "home_emergency", "legal_expenses")


def _caller_account(d, p):
    """The account the caller has proved: a verified principal's own, or the one proved by a matching policy number and date of birth."""
    if p.get("verified") and p.get("account_id"):
        return p["account_id"]
    return d["verified"].get(p["id"])


def s_lookup_policy(d, a, p):
    num, dob = a.get("policy_number"), a.get("date_of_birth")
    ph = next((x for x in d["fixture"]["policyholders"] if x["policy_number"] == num), None)
    if ph is None or ph["date_of_birth"] != dob:
        return _err("identity_not_verified", "Identity could not be verified.")
    if p.get("verified") and p.get("account_id") and p["account_id"] != ph["account_id"]:
        return _err("identity_not_verified", "Identity could not be verified.")
    d["verified"][p["id"]] = ph["account_id"]
    keep = {k: v for k, v in ph.items() if k != "date_of_birth"}
    return _ok({"identity_verified": True, **copy.deepcopy(keep)})


def s_check_claim(d, a, p):
    acct = _caller_account(d, p)
    if acct is None:
        return _err("identity_not_verified", "Verify identity first with lookup_policy.")
    claim = next((c for c in d["fixture"]["claims"] if c["claim_id"] == a.get("claim_id")), None)
    if claim is None or claim["account_id"] != acct:
        return _err("not_found_for_principal", "No such claim for this person.")
    return _ok({"claim_id": claim["claim_id"], "status": claim["status"], "claim_type": claim["claim_type"],
                "date_of_loss": claim["date_of_loss"], "history": copy.deepcopy(claim["history"])})


def s_open_claim(d, a, p):
    acct = _caller_account(d, p)
    if acct is None:
        return _err("identity_not_verified", "Verify identity first with lookup_policy.")
    ph = next((x for x in d["fixture"]["policyholders"] if x["policy_number"] == a.get("policy_number")), None)
    if ph is None or ph["account_id"] != acct:
        return _err("forbidden", "That policy is not the caller's own.")
    loss = _parse_d(a.get("date_of_loss"))
    if loss is None:
        return _err("invalid_date", "date_of_loss must be a date like 2026-11-03")
    if loss > TODAY:
        return _err("future_date", "date_of_loss cannot be in the future.")
    if a.get("claim_type") not in CLAIM_TYPES:
        return _err("invalid_claim_type", "claim_type must be one of " + ", ".join(CLAIM_TYPES))
    if not str(a.get("description", "")).strip():
        return _err("missing_argument", "description is required.")
    n = len(d["fixture"]["claims"]) + len(d["claims"]) + 1
    claim = {"claim_id": f"CLM-26-{9000 + n}", "account_id": acct, "policy_number": ph["policy_number"], "claim_type": a["claim_type"],
             "date_of_loss": a["date_of_loss"], "description": str(a["description"])[:500], "status": "received",
             "history": [{"status": "received", "date": TODAY.isoformat(), "note": "Opened by the assistant"}], "settlement_amount_gbp": None}
    d["claims"].append(claim)
    d["fixture"]["claims"].append(claim)
    d["counts"]["claims_opened"] += 1
    return _ok({k: claim[k] for k in ("claim_id", "policy_number", "claim_type", "date_of_loss", "status")}, True, d)


HANDLERS = {
    "quillon": {"lookup_account": q_lookup_account, "create_quote": q_create_quote, "book_demo": q_book_demo},
    "juniper": {"check_slots": j_check_slots, "book_appointment": j_book_appointment, "hand_off": j_hand_off},
    "saltmarsh": {"lookup_policy": s_lookup_policy, "check_claim": s_check_claim, "open_claim": s_open_claim},
}
