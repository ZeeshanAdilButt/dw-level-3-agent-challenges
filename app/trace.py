"""Spans with ids, parent ids and inclusive durations. One Tracer per request; spans nest by a stack."""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import asdict

from .types import Span


class Tracer:
    def __init__(self, request_id: str = "", clock=time.perf_counter):
        self.request_id = request_id
        self._clock = clock
        self._t0 = clock()
        self.spans: list[Span] = []
        self._stack: list[Span] = []
        self._calls = 0

    def now_ms(self) -> float:
        return (self._clock() - self._t0) * 1000.0

    def next_call(self) -> int:
        """Counts model calls, so each call gets its own seed."""
        self._calls += 1
        return self._calls

    @contextmanager
    def span(self, name: str, **attrs):
        sp = Span(span_id=f"sp-{len(self.spans) + 1}",
                  parent_id=self._stack[-1].span_id if self._stack else None,
                  name=name, start_ms=self.now_ms(), end_ms=0.0, attrs=dict(attrs))
        self.spans.append(sp)
        self._stack.append(sp)
        try:
            yield sp
        finally:
            sp.end_ms = max(self.now_ms(), sp.start_ms)
            self._stack.pop()

    def export(self) -> list[dict]:
        out = []
        for sp in self.spans:
            d = asdict(sp)
            if not d["end_ms"]:
                d["end_ms"] = self.now_ms()
            out.append(d)
        return out
