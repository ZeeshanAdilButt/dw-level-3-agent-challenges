"""Juniper Lane Clinic's hard rules as code: no diagnosis, no medicine or weight advice, red flags get the emergency number
and an urgent handoff, ask only what a booking needs, never another patient's details, verify before a booking."""
from __future__ import annotations

import re

from .common import Decision

RED_FLAGS = [
    ("chest or arm symptoms", re.compile(r"(chest.{0,40}(pain|crush|tight|pressure|hurts?))(?=.{0,80}(arm|jaw|numb|sweat|breath))|"
                                         r"(arm.{0,30}(numb|dead|heavy|tingl)).{0,80}chest|crushing chest|chest pain.{0,60}arm", re.I)),
    ("face, speech or weakness symptoms", re.compile(r"(face.{0,25}(droop|dropping|sagging))|slurred speech|speech.{0,12}slurred|can'?t (lift|move) (my|his|her) arm", re.I)),
    ("severe breathing difficulty", re.compile(r"can'?t breathe|cannot breathe|struggling to breathe|gasping|severe(ly)? (short of breath|breathing)|breathing (is )?(very )?(bad|hard|difficult)", re.I)),
    ("severe allergic-type reaction", re.compile(r"anaphyla|throat (is )?(closing|swelling)|tongue (is )?swelling|swelling.{0,20}(throat|tongue|face).{0,40}(breath|sting|ate|eaten)", re.I)),
    ("heavy bleeding", re.compile(r"(heavy|severe|won'?t stop|can'?t stop|soaking).{0,20}bleeding|bleeding.{0,25}(won'?t stop|heavily|a lot|badly)", re.I)),
    ("thoughts of self-harm", re.compile(r"suicid|kill myself|end(ing)? it all|end my life|want to die|don'?t want to live|hurt myself", re.I)),
]
MEDICINE = re.compile(r"\b(dose|dosage|\d+\s?mg|(take|taking|stop|stopping|start|starting|increase|reduce|skip|double|halve)\b.{0,40}"
                      r"\b(tablets?|pills?|medicine|medication|medicines|statin|insulin|antibiotics?|paracetamol|ibuprofen|aspirin|inhaler))\b", re.I)
WEIGHT = re.compile(r"\b(lose|losing|loss of)\b.{0,20}\b(weight|kilos?|kg|stones?|pounds)\b|\bweight[- ]loss\b|\bdiet\b.{0,40}\blose\b|\bslimming\b", re.I)
DIAGNOSIS_ASK = re.compile(r"what('s| is) wrong with me|what do i have|do i have (a |an )?(\w+ ){0,2}(cancer|infection|diabet\w*|asthma|anxiety|depression|cold|flu|virus|tumou?r|condition|disease|disorder)|is it (a |an )?(\w+ ){0,2}(cancer|infection|tumou?r|diabet|asthma|anxiety|depress)|"
                           r"am i (having|dying)|probably just \w+, right", re.I)
OTHER_PERSON = re.compile(r"\b(neighbou?r|friend|colleague|co-?worker|boss|ex[- ]?(wife|husband|partner)|someone else|another patient|stranger)\b.{0,80}\b(appointment|booking|record|"
                          r"results?|details|prescription|number|address|time|date)\b|what time is (her|his|their|\w+'s) appointment", re.I)
BOOKING = re.compile(r"\b(book|rebook|reschedule|put me down|cancel my)\b|\bmy (booking|appointment)\b", re.I)
SAFE_NOW = re.compile(r"\b(i'?m|i am|we are|he is|she is) (safe|okay|ok|fine now)|ambulance (is )?(here|arrived)|help has arrived", re.I)
SYMPTOMS = re.compile(r"\b(chest|arm|breath\w*|bleed\w*|droop\w*|slurr\w*|speech|throat|tongue|numb\w*|tingl\w*|pains?|painful|hurts?|"
                      r"tight\w*|dizz\w*|faint\w*|sweat\w*|swell\w*|symptoms?|worse)\b", re.I)   # "I'm ok" next to any of these is not safe

DIAG_WORDING = [
    re.compile(r"\b(you|it|that|this)('?s| is| are| may be| might be| could be| probably| likely| sounds like)\b.{0,30}\b(infection|indigestion|heartburn|angina|"
               r"asthma|diabetes|anxiety|depression|migraine|flu|virus|viral|an?a?emia|arthritis|sprain|allergy|eczema|hypertension|condition|syndrome|disease|disorder)\b", re.I),
    re.compile(r"\b(probably|likely|sounds like|looks like|could be|might be|may be|consistent with|a sign of|symptom of)\b.{0,25}\b(indigestion|infection|heartburn|angina|"
               r"asthma|diabetes|anxiety|depression|migraine|flu|virus|viral|an?a?emia|arthritis|allergy|eczema|hypertension)\b", re.I),
    re.compile(r"\byou (should|can|could|may|must|need to|ought to)\b.{0,15}\b(take|stop|start|increase|reduce|skip|double)\b.{0,30}"
               r"\b(mg|tablets?|pills?|dose|medicine|medication|paracetamol|ibuprofen|aspirin|antibiotics?|statins?|insulin)\b", re.I),
]
MEDICAL_REASON = re.compile(r"reason for (your |the )?(visit|appointment)|what symptoms|describe your symptoms|what('s| is) wrong\b", re.I)


class JuniperRules:
    """Starter: no hard rules. Lab 5 part 2 writes them (before the model, after the model, the classifier categories)."""
    uses_classifier = False
    force_authority = False

    def __init__(self, fixture: dict, settings: dict):
        self.fixture = fixture
        self.settings = settings

    def before(self, msg, state, tools_on: bool):
        return None

    def classify_category(self, category: str, msg, state, tools_on: bool):
        return None

    def after(self, text: str, ctx: dict):
        return None
