"""Two-sided exact sign test and the verdict wording (notes, section 3)."""
from math import comb

ALPHA = 0.05


def sign_test(fixed: int, broken: int) -> float:
    """Two-sided exact binomial p-value for `fixed` against `broken`, ties already dropped.

    p = min(1, 2 * P(X <= min(fixed, broken))) with X ~ Binomial(n, 1/2), n = fixed + broken. n = 0 gives 1.
    """
    n = fixed + broken
    if n == 0:
        return 1.0
    k = min(fixed, broken)
    tail = sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def fmt_p(p: float) -> str:
    """Three decimals, a half rounded up, as the dashboard prints it (0.0625 is 0.063 in both)."""
    from decimal import Decimal, ROUND_HALF_UP
    return str(Decimal(repr(min(1.0, p))).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def verdict(fixed: int, broken: int, alpha: float = ALPHA) -> str:
    p = sign_test(fixed, broken)
    if p < alpha and fixed > broken:
        return "evidence of improvement on this set"
    if p < alpha and broken > fixed:
        return "evidence of harm"
    return "inconclusive"
