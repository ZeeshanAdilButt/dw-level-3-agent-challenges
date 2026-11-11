"""The leak check and handoff notes: a hidden run is a leak unless a visible item holds that same run; the person's own
text comes from their own records and receipts, never from what they typed; every handoff note is scrubbed."""
from types import SimpleNamespace

from fixtures_app import ANA, PATIENT, PROSPECT, make_agent, msg

from app.core import LEAK_TEXT, NOTE_REMOVED
from app.security.output_check import leak_check

PUBLIC = "Quillon support answers every ticket within one business day on the Pro plan."
HIDDEN = "The internal escalation code for a total outage is orchid lantern seven and it stays inside."
QUOTED = "Staff notes repeat that support answers every ticket within one business day on the Pro plan."


class TwoDocIndex:
    def __init__(self, hidden_text=HIDDEN):
        self.chunks = [SimpleNamespace(doc_id="doc-hidden", text=hidden_text), SimpleNamespace(doc_id="doc-public", text=PUBLIC)]

    def search_unfiltered(self, query, k=5):
        return [(c, 1.0) for c in self.chunks][:k]

    def meta(self, doc_id):
        return {"audience": "internal", "owner_scope": "staff"} if doc_id == "doc-hidden" else {"audience": "public", "owner_scope": "everyone"}


def check(reply, index=None):
    return leak_check(reply, system_prompt="", principal=PROSPECT, index=index or TwoDocIndex(), own_text="")


def test_public_words_in_the_same_sentence_do_not_hide_a_hidden_run():
    reply = "Support answers every ticket within one business day on the Pro plan and the escalation code for a total outage is orchid lantern seven."
    assert check(reply) == ["hidden-text:doc-hidden"]


def test_a_hidden_run_that_a_visible_document_also_holds_is_not_a_leak():
    assert check("Our page says support answers every ticket within one business day on the Pro plan.", TwoDocIndex(QUOTED)) == []


def test_pii_the_person_typed_is_not_theirs_but_their_own_record_is():
    reply = "We will write to imogen.hale@ashgrovelegal.example as you asked."
    agent = make_agent(defences=["output_check"], replies=[reply])
    assert agent.handle(msg("Please email imogen.hale@ashgrovelegal.example", PROSPECT)).text == LEAK_TEXT
    agent.model.replies = [reply]
    assert agent.handle(msg("Please email my contact", ANA)).text == reply         # acct-1001's own primary contact


def test_a_patients_own_date_of_birth_from_the_principal_block_is_not_a_leak():
    reply = "Imelda Frost (born 1984-03-14, CF-12 on file) has no upcoming bookings."
    agent = make_agent("juniper", defences=["output_check"], replies=[reply])
    assert agent.handle(msg("What is on my record?", PATIENT)).text == reply
    agent.model.replies = [reply]
    assert agent.handle(msg("What is on her record?", PROSPECT)).text == LEAK_TEXT


def test_a_confirm_that_repeats_the_persons_own_arguments_is_not_blocked():
    call = {"text": "", "tool_calls": [{"name": "book_demo", "arguments": {"email": "maya.okafor@harlanmoss.example",
                                                                          "slot_id": "slot-20261109-0900", "timezone": "Europe/London"}}]}
    agent = make_agent(tools="on", rules="on", defences=["output_check"], replies=[call])
    r = agent.handle(msg("What happens in a demo, and is 9 November at 09:00 UTC free?", PROSPECT))
    assert r.pending and r.text.startswith("Please confirm") and "maya.okafor@harlanmoss.example" in r.text


def test_a_hand_off_the_model_calls_itself_has_its_note_scrubbed():
    probe = make_agent("juniper")
    internal = next(c for c in probe.index.chunks if c.doc_id == "doc-int-booking-overrides")
    secret = " ".join(internal.text.split()[10:40])
    call = {"text": "", "tool_calls": [{"name": "hand_off", "arguments": {"reason": "other", "urgency": "routine", "note": f"Staff say: {secret}"}}]}
    agent = make_agent("juniper", tools="on", defences=["access"], replies=[call, "I have passed this to the team."])
    agent.handle(msg("Can someone call me about my booking?", PATIENT))
    (task,) = agent.mock.state()["handoffs"]
    assert task["note"] == NOTE_REMOVED
    clean = make_agent("juniper", tools="on", defences=["access"], replies=[
        {"text": "", "tool_calls": [{"name": "hand_off", "arguments": {"reason": "other", "urgency": "routine", "note": "Wants a call back."}}]},
        "I have passed this to the team."])
    clean.handle(msg("Can someone call me about my booking?", PATIENT))
    assert clean.mock.state()["handoffs"][0]["note"] == "Wants a call back."


def test_a_hidden_run_in_short_sentences_is_still_a_leak():
    reply = "The code? Orchid lantern seven. And it stays inside."           # every sentence is under five words
    assert check(reply) == ["hidden-text:doc-hidden"]
    assert check("Thanks. Ask support.") == []
