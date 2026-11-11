"""A link the access check cuts is named in the case record (rule_hits), not silently dropped."""
import os
from pathlib import Path

from app.core import Agent
from app.settings import load_settings
from app.types import Message, Principal

from mock_api import MockClient

ROOT = Path(__file__).resolve().parents[2]


def test_link_hop_records_the_refused_link():
    os.environ["DW_MODEL_PATH"] = "stub"
    pack = ROOT / "packs" / "quillon"
    agent = Agent(load_settings({"pack": "quillon", "context": "link_hop", "defences": ["access"]}), pack, MockClient(pack, "t"))
    idx = agent.index
    src, target = next((d.doc_id, t) for d in idx.docs.values() for t in d.links
                       if t in idx.docs and idx.meta(t).get("audience") == "internal" and idx.meta(d.doc_id).get("audience") != "internal")
    reply = agent.handle(Message("q1", "c", Principal("v", "prospect", False, None), idx.docs[src].title))
    assert f"link_refused:{target}" in reply.eval.rule_hits
