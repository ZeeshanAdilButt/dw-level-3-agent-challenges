"""Marking: untrusted text is wrapped, labelled with its document id, and cannot close its own wrapper."""
import re

_END = re.compile(r"</\s*document\b[^>]*>", re.I)          # also an end marker with attributes
_START = re.compile(r"<\s*document\b", re.I)


def neutralise(text: str) -> str:
    """Remove anything in the text that looks like our start or end marker."""
    return _START.sub("[start marker removed]", _END.sub("[end marker removed]", text))


def wrap(doc_id: str, title: str, text: str) -> str:
    """Starter: the text goes through as it is. Lab 7 part 2 wraps and labels it."""
    return title + " " + text
