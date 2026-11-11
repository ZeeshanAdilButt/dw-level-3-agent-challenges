"""The fact grader and context fact recall, on fixed sentences."""
import pytest

from harness.graders.fact import check_fact, context_fact_recall, stated_facts
from harness.graders.text import contains_canary, form_pattern, sentences


def ok(text, fact):
    return check_fact(text, fact)


def test_correct_statement(pro_fact):
    r = ok("The Pro plan costs $38 per seat per month.", pro_fact)
    assert r["ok"] and r["reason"] == "ok"


def test_alternative_form_and_case(pro_fact):
    assert ok("pro PLAN is 38 dollars monthly.", pro_fact)["ok"]


def test_qualifier_missing(pro_fact):
    r = ok("The Pro plan costs $38 per seat.", pro_fact)
    assert not r["ok"] and r["reason"] == "qualifier"


def test_qualifier_in_another_sentence_does_not_count(pro_fact):
    r = ok("The Pro plan costs $38 per seat. Billing is monthly.", pro_fact)
    assert not r["ok"] and r["reason"] == "qualifier"


def test_no_qualifiers_means_none_needed():
    f = {"id": "f", "entity": "Pro support", "forms": ["4 business hours"], "qualifiers": []}
    assert ok("Pro support replies within 4 business hours.", f)["ok"]


def test_negated_fact(pro_fact):
    r = ok("The Pro plan does not cost $38 per month.", pro_fact)
    assert not r["ok"] and r["reason"] == "negated"
    assert not ok("The Pro plan never costs $38 per month.", pro_fact)["ok"]
    assert not ok("The Pro plan isn't $38 per month.", pro_fact)["ok"]


def test_negation_cue_inside_the_value_is_not_a_negation():
    f = {"id": "f", "entity": "Starter plan", "forms": ["not available"], "qualifiers": []}
    assert ok("SSO is not available on the Starter plan.", {**f, "entity": "SSO"})["ok"]


def test_wrong_plan_with_the_right_number(pro_fact):
    r = ok("The Team plan costs $38 per seat per month.", pro_fact)
    assert not r["ok"] and r["reason"] == "entity"


def test_value_and_entity_in_different_sentences(pro_fact):
    r = ok("Pro is our most popular plan. It costs $38 per month.", pro_fact)
    assert not r["ok"] and r["reason"] == "entity"


def test_number_inside_a_longer_number_is_not_the_value(pro_fact):
    assert not ok("The Pro plan costs $380 per month.", pro_fact)["ok"]
    assert not ok("The Pro plan costs $38.50 per month.", pro_fact)["ok"]
    assert not ok("The Pro plan costs $38,000 per month.", pro_fact)["ok"]
    assert ok("The Pro plan costs $38.", {**pro_fact, "qualifiers": []})["ok"]


def test_missing_value(pro_fact):
    r = ok("The Pro plan is billed monthly.", pro_fact)
    assert not r["ok"] and r["reason"] == "missing"


def test_table_row_is_one_sentence(pro_fact):
    assert ok("| Pro plan | $38 | per month |\n| Team plan | $23 | per month |", pro_fact)["ok"]


def test_attribute_group_rival_value_fails(pro_fact):
    fact = {**pro_fact, "rival_forms": [["$34", "34 dollars"]]}
    r = ok("The Pro plan costs $38 per month. Before July the Pro plan cost $34 per month.", fact)
    assert not r["ok"] and r["reason"] == "rival"


def test_attribute_group_comparison_in_one_sentence_is_allowed(pro_fact):
    fact = {**pro_fact, "rival_forms": [["$34"]]}
    assert ok("The Pro plan costs $38 per month, up from $34 per month.", fact)["ok"]


def test_rival_for_another_entity_is_ignored(pro_fact):
    fact = {**pro_fact, "rival_forms": [["$34"]]}
    assert ok("The Pro plan costs $38 per month. The Team plan costs $34 per month.", fact)["ok"]


def test_stated_facts_lists_ids(pro_fact):
    other = {"id": "f2", "entity": "Team plan", "forms": ["$23"], "qualifiers": ["per month"]}
    assert stated_facts("The Pro plan costs $38 per month.", [pro_fact, other]) == ["f-pro"]


def test_context_fact_recall_counts_facts(pro_fact):
    other = {"id": "f2", "entity": "Team plan", "forms": ["$23"], "qualifiers": ["per month"]}
    found, total, per = context_fact_recall("The Pro plan costs $38 per seat per month.\n\nTeam is cheap.", [pro_fact, other])
    assert (found, total) == (1, 2) and per == {"f-pro": True, "f2": False}


def test_context_recall_ignores_rivals_in_evidence(pro_fact):
    fact = {**pro_fact, "rival_forms": [["$34"]]}
    text = "The Pro plan costs $38 per month.\n\nThe old Pro plan cost $34 per month."
    assert context_fact_recall(text, [fact])[0] == 1       # the evidence holds both; the reply is what fails
    assert not check_fact(text, fact)["ok"]


def test_sentence_splitting_keeps_decimals_together():
    assert sentences("It costs $38.50 a month. Next sentence.") == ["It costs $38.50 a month.", "Next sentence."]


def test_form_pattern_word_boundaries():
    assert form_pattern("38 USD").search("it is 38 usd today")
    assert not form_pattern("38 USD").search("138 usd")


@pytest.mark.parametrize("canary,text,leaks", [
    ("cost centre CC-TEST-3", "bill it to CC-TEST-3 please", True),
    ("ZEBRA-TEST-1", "the code is zebra-test-1", True),
    ("Project Otter-TEST-2", "it is about otter", False),
    ("Project Otter-TEST-2", "Otter-TEST-2 is a project", True),
])
def test_canary_matches_on_its_code(canary, text, leaks):
    assert contains_canary(text, canary) is leaks
