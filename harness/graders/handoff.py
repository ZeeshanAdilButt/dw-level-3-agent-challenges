"""Handoff grader: handed off, with a note for the person (and urgent when the rule says urgent)."""
from .actions import executed, handoff_of

def handed_off(step: dict) -> bool:
    return False      # starter: nothing counts as a handoff until the handoff grader is written


def grade_handoff(step: dict, urgent: bool = False) -> dict:
    raise NotImplementedError("YOUR TURN: lab 5, 5.6: write the handoff grader")
