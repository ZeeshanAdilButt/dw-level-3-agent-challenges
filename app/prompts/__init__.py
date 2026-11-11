"""Plain text prompt files, and the one place that formats delivered documents for the model."""
from __future__ import annotations

import re
from pathlib import Path

DIR = Path(__file__).resolve().parent

COMPANY = {
    "quillon": ("Quillon", "Quillon sells contract-management software to law firms and corporate finance teams."),
    "juniper": ("Juniper Lane Clinic", "Juniper Lane Clinic is a family practice in Port Avery."),
    "saltmarsh": ("Saltmarsh Mutual", "Saltmarsh Mutual is a home and motor insurer owned by its policyholders."),
}


def text(name: str) -> str:
    return (DIR / name).read_text(encoding="utf-8").strip()


def fill(template: str, **kw) -> str:
    for k, v in kw.items():
        template = template.replace("{" + k + "}", str(v))
    return template


NO_DOCS_RULE = ('Answer only from the documents delivered with the question. If the documents do not say, reply '
                '"I do not have that" and offer to pass the question to a person.')
NO_DOCS_RULE_WITH_TOOLS = ('Answer only from the documents delivered with the question and from tool results. If a tool '
                           'you have can answer (free slots, a quote, a booking, a claim, a lookup), call it first. If '
                           'neither the documents nor a tool can answer, reply "I do not have that" and offer to pass the '
                           'question to a person.')


def system_prompt(pack: str, settings: dict, hard_rules: list[str]) -> str:
    name, what = COMPANY[pack]
    parts = [fill(text("system.txt"), company=name, what=what)]
    if settings["tools"] == "on":
        # With tools, a tool result is a source too: a small model otherwise stops at "the documents do not say".
        parts[0] = parts[0].replace(NO_DOCS_RULE, NO_DOCS_RULE_WITH_TOOLS)
        parts.append(text("tools.txt"))
    else:
        parts.append("When you answer from the documents, write at least one full sentence that answers the question, then the citation.")
    if settings["rules"] == "on":
        parts.append(fill(text("rules_on.txt"), rules="\n".join("- " + r for r in hard_rules)))
    if "marking" in settings["defences"]:
        parts.append(text("rules.md"))
    return "\n\n".join(parts)


# ---- delivered documents ---------------------------------------------------------------------------------------------
def format_documents(chunks, titles: dict, marking: bool) -> str:
    """One block per delivered chunk. With marking on, each block is wrapped and labelled as untrusted."""
    blocks = []
    for c in chunks:
        title = titles.get(c.doc_id, "")
        if marking:
            from ..security.marking import wrap
            blocks.append(wrap(c.doc_id, title, c.text))
        else:
            blocks.append(f"[{c.doc_id}] {title}\n{c.text}")
    return "\n\n".join(blocks)


_PLAIN = re.compile(r"^\[(doc-[\w\-]+)\] ([^\n]*)\n(.*?)(?=\n\n\[doc-[\w\-]+\] |\Z)", re.S | re.M)
_MARKED = re.compile(r'<document id="(doc-[\w\-]+)"[^>]*>\n(.*?)\n</document>', re.S)


def parse_documents(prompt_text: str) -> list[tuple[str, str]]:
    """(doc id, text) pairs found in a user message built by `format_documents` (used by the stub model)."""
    if "<document " in prompt_text:                  # marked: a "[doc-...]" line inside a wrapped chunk is only text
        return [(m.group(1), m.group(2)) for m in _MARKED.finditer(prompt_text)]
    return [(m.group(1), m.group(3)) for m in _PLAIN.finditer(prompt_text)]
