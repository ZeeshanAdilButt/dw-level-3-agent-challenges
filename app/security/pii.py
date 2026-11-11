"""PII patterns (shipped). Each is a plain regex over reply text."""
import re

PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    "phone": re.compile(r"(?<!\d)(?:\+\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s-]?)\d{3}[\s-]?\d{3,4}(?!\d)"),
    "card": re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)"),
    "date_of_birth": re.compile(r"\b(?:born|dob|date of birth)\b[^.\n]{0,20}\d", re.I),
    "member_number": re.compile(r"\b(?:HL\d{7}|TW\d{8}|PG-\d{6}|CB\d{5,}|AH\d{5,})\b"),
    "policy_number": re.compile(r"\bSM-[HM]-\d{6}\b"),
}
ROLE_MAILBOXES = {"support", "sales", "billing", "info", "hello", "help", "contact", "claims", "reception", "privacy",
                  "security", "legal", "press", "complaints", "enquiries", "bookings", "accounts", "careers"}


def find(text: str) -> list[tuple[str, str]]:
    out = []
    for name, rx in PATTERNS.items():
        for m in rx.finditer(text):
            val = m.group(0)
            if name == "email" and val.split("@")[0].lower() in ROLE_MAILBOXES:
                continue
            out.append((name, val))
    return out
