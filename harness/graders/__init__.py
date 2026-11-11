"""Graders. They read stored step results only, so `harness diff` can regrade old runs with today's code."""
from .case import FAILURE_ORDER, grade_case

# Bump this when a grader's behaviour changes; every run record and every diff prints it (decision B3).
GRADER_VERSION = "graders-1.0.0"

__all__ = ["GRADER_VERSION", "FAILURE_ORDER", "grade_case"]
