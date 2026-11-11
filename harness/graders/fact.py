"""Fact grader (decision D1) and context fact recall.

A key fact is a dict: {"id", "entity", "forms": [...], optional "qualifiers": [...], optional "rival_forms": [[...], ...]}.
`rival_forms` lists the accepted forms of other values for the same attribute and entity (the attribute group).

A reply states the fact when one sentence holds a form of the value, names the entity, holds at least one
qualifier (when the fact has any), and is not negated. A reply that states a different value of the same
attribute for the entity fails, unless that very sentence also states the right value (a comparison).
"""
from .text import has_entity, has_form, is_negated, norm, sentences

def check_fact(text: str, fact: dict, rivals: bool = True) -> dict:
    raise NotImplementedError("YOUR TURN: lab 1, 1.6: write the fact grader (value, entity, qualifiers, negation, attribute group)")


def stated_facts(text: str, facts: list) -> list:
    """The ids of the key facts a text states under check_fact."""
    return [f["id"] for f in facts if check_fact(text, f)["ok"]]


def context_fact_recall(delivered_text: str, facts: list) -> tuple:
    raise NotImplementedError("YOUR TURN: lab 2, 2.5: write context fact recall (key facts present in the delivered text)")
