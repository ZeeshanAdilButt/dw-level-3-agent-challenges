"""The mock as a FastAPI server: POST /ns/{ns}/tools/{name}, GET /ns/{ns}/state, POST /ns/{ns}/reset.

State is per namespace, created on first use for the pack named by the `X-DW-Pack` header (or `?pack=`), else the default.
Run: `uvicorn mock_api.server:app --port 8100`, then set MOCK_API_URL=http://localhost:8100.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request

from . import HttpMockClient, MockClient  # noqa: F401  (HttpMockClient is re-exported here as INTERFACES.md names it)

PACKS = Path(__file__).resolve().parents[1] / "packs"


def create_app(packs_dir: Path | None = None, default_pack: str | None = None) -> FastAPI:
    packs_dir = Path(packs_dir or PACKS)
    default_pack = default_pack or os.environ.get("DW_PACK", "quillon")
    app = FastAPI(title="Mock company API")
    spaces: dict[tuple[str, str], MockClient] = {}
    lock = threading.Lock()

    def space(ns: str, pack: str | None) -> MockClient:
        pack = pack or default_pack
        if not (packs_dir / pack / "tools" / "fixture.json").exists():
            raise HTTPException(404, f"unknown pack {pack}")
        with lock:
            key = (ns, pack)
            if key not in spaces:
                spaces[key] = MockClient(packs_dir / pack, ns)
            return spaces[key]

    @app.post("/ns/{ns}/tools/{name}")
    async def call_tool(ns: str, name: str, request: Request, x_dw_pack: str | None = Header(None), pack: str | None = None):
        body = await request.json()
        principal = body.get("principal") or {}
        if "id" not in principal:
            raise HTTPException(422, "principal.id is required")
        key = body.get("idempotency_key")
        if not key:
            raise HTTPException(422, "idempotency_key is required")
        return space(ns, x_dw_pack or pack).call(name, body.get("args") or {}, principal, key)

    @app.get("/ns/{ns}/state")
    def get_state(ns: str, x_dw_pack: str | None = Header(None), pack: str | None = None):
        return space(ns, x_dw_pack or pack).state()

    @app.post("/ns/{ns}/reset")
    def reset(ns: str, x_dw_pack: str | None = Header(None), pack: str | None = None):
        space(ns, x_dw_pack or pack).reset()
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
