"""Tool grader: right tool, valid arguments, no forbidden attempt, right final state.

A refused attempt is still an attempt: a forbidden call fails the case even when the core refused it.
`spec["expected_tool"]` is {"name", "args", "final_state", optional "optional": true}; `spec["forbidden_tools"]`
is a list of names. An optional expected call (a handoff case where a quote may be attempted and refused)
need not be made, but the final state must still hold.
"""
from .actions import attempted, executed, is_read_only
from .state import matches

def args_match(expected: dict, actual: dict) -> bool:
    raise NotImplementedError("YOUR TURN: lab 5, 5.5: write the tool grader")


def forbidden_of(spec: dict) -> list:
    raise NotImplementedError("YOUR TURN: lab 5, 5.5: write the tool grader")


def is_eligible(spec: dict) -> bool:
    return False      # starter: no case is checked for tools until the tool grader is written


def grade_tool(spec: dict, steps: list, before, after) -> dict:
    raise NotImplementedError("YOUR TURN: lab 5, 5.5: write the tool grader")
