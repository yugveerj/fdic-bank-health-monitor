"""Experiment-analysis primitives — pure functions, no warehouse I/O, so every
rule is unit-testable. Normal approximations throughout: at the arm sizes GA4
traffic produces (tens of thousands of users), exact tests buy nothing.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import stats


def required_n_per_arm(p_baseline: float, rel_mde: float,
                       alpha: float = 0.05, power: float = 0.8) -> int:
    """Users per arm to detect a relative lift of `rel_mde` on a baseline
    conversion rate with a two-sided two-proportion z-test — the standard
    pooled-variance normal-approximation formula, rounded up."""
    p1 = p_baseline
    p2 = p_baseline * (1 + rel_mde)
    if not (0 < p1 < 1 and 0 < p2 < 1):
        raise ValueError(f"conversion rates must be in (0, 1): baseline {p1}, lifted {p2}")
    p_bar = (p1 + p2) / 2
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    numer = (z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
             + z_power * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return math.ceil(numer / (p2 - p1) ** 2)


def two_proportion_ztest(conv_a: int, n_a: int, conv_b: int, n_b: int) -> tuple[float, float]:
    """Pooled two-proportion z-test. z is signed b minus a (treatment minus
    control by convention); p is two-sided."""
    p_a, p_b = conv_a / n_a, conv_b / n_b
    p_pool = (conv_a + conv_b) / (n_a + n_b)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    z = (p_b - p_a) / se
    return float(z), float(2 * stats.norm.sf(abs(z)))


def srm_check(n_a: int, n_b: int, expected_ratio: float = 0.5) -> tuple[float, float]:
    """Chi-square goodness of fit of arm sizes against the intended split.
    A small p means assignment itself is broken and every downstream metric
    is suspect — this runs before anything else gets read."""
    total = n_a + n_b
    expected = [total * expected_ratio, total * (1 - expected_ratio)]
    chi2, p = stats.chisquare([n_a, n_b], f_exp=expected)
    return float(chi2), float(p)


def apply_synthetic_lift(conversions: int, n: int, rel_lift: float, seed: int) -> int:
    """Inject a known true effect: each of the n − conversions non-converters
    converts with the probability that yields `rel_lift` in expectation, one
    binomial draw from a seeded numpy Generator so the result reproduces
    exactly. This simulates a treatment whose true effect size we chose — it
    exists to show the pipeline detects an effect of the planned size, not to
    discover one. The return is bounded by n by construction."""
    if not 0 <= conversions < n:
        raise ValueError(f"need 0 <= conversions < n, got {conversions}/{n}")
    p_add = conversions * rel_lift / (n - conversions)
    if not 0 <= p_add <= 1:
        raise ValueError(f"lift {rel_lift} unreachable: implies conversion prob {p_add:.3f}")
    extra = np.random.default_rng(seed).binomial(n - conversions, p_add)
    return conversions + int(extra)
