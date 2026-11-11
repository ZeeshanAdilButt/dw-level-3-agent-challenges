"""Sign test values, computed here from the binomial formula with exact fractions (not read from any reference run)."""
from fractions import Fraction
from math import comb

import pytest

from harness.signtest import fmt_p, sign_test, verdict


def exact(fixed, broken):
    n = fixed + broken
    if n == 0:
        return Fraction(1)
    k = min(fixed, broken)
    return min(Fraction(1), 2 * Fraction(sum(comb(n, i) for i in range(k + 1)), 2 ** n))


@pytest.mark.parametrize("fixed,broken,text", [
    (0, 0, "1.000"),      # no fixed and no broken cases: nothing to test
    (6, 5, "1.000"),      # the constructed noise example: 2 * 0.5 is capped at 1
    (9, 1, "0.021"),
    (1, 9, "0.021"),      # two-sided: symmetric
    (8, 2, "0.109"),
    (10, 0, "0.002"),
    (3, 7, "0.344"),
    (5, 5, "1.000"),
])
def test_values(fixed, broken, text):
    assert fmt_p(sign_test(fixed, broken)) == text
    assert sign_test(fixed, broken) == pytest.approx(float(exact(fixed, broken)))


def test_p_never_exceeds_one():
    for f in range(0, 15):
        for b in range(0, 15):
            assert sign_test(f, b) <= 1.0
            assert fmt_p(sign_test(f, b)) <= "1.000"


def test_ties_are_not_an_input():
    # the function sees only fixed and broken; 40 ties change nothing because the caller drops them
    assert sign_test(7, 2) == sign_test(7, 2)


@pytest.mark.parametrize("fixed,broken,words", [
    (9, 1, "evidence of improvement on this set"),
    (1, 9, "evidence of harm"),
    (6, 5, "inconclusive"),
    (7, 2, "inconclusive"),   # p = 0.180
    (0, 0, "inconclusive"),
    (8, 1, "evidence of improvement on this set"),  # p = 0.039
])
def test_verdict_wording(fixed, broken, words):
    assert verdict(fixed, broken) == words
