"""Idempotency (decision C3). The key is (principal id, conversation id, request id) plus a hash of the request.

`reserve` is atomic: of two concurrent callers with the same key exactly one gets "new"; the other gets "in_progress".
`complete` stores the reply; a later caller with the same key and the same request hash gets "done" and the stored reply.
A reply is never found through another principal's key, because the principal id is part of the key.
"""
from __future__ import annotations

import copy
import hashlib
import threading


def request_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class IdempotencyStore:
    """Starter: a plain dict and no lock. Lab 5 part 1 makes the reservation atomic."""

    def __init__(self):
        self._entries: dict[tuple, dict] = {}

    def reserve(self, key: tuple, req_hash: str):
        e = self._entries.get(key)
        if e is None:
            self._entries[key] = {"hash": req_hash, "state": "running", "reply": None}
            return "new", None
        if e["hash"] != req_hash:
            return "conflict", None
        if e["state"] == "running":
            return "in_progress", None
        return "done", e["reply"]

    def complete(self, key: tuple, reply) -> None:
        self._entries[key].update(state="done", reply=reply)

    def release(self, key: tuple) -> None:
        self._entries.pop(key, None)
