"""The experiment-analysis primitives, on known inputs: the sample-size
formula must match the textbook value, the z-test must call an obvious
difference and pass an obvious null, the SRM check must flag a broken split
without crying wolf on noise, and the synthetic lift must reproduce exactly —
that determinism is what makes the sample experiment rerunnable."""

import pytest

from analysis import ab


def test_required_n_matches_textbook_value():
    # p1=0.10 vs p2=0.12, alpha 0.05, power 0.8: pooled-variance formula
    # gives 3841 per arm (computed by hand, matches published tables)
    assert ab.required_n_per_arm(0.10, 0.20) == pytest.approx(3841, rel=0.01)


def test_required_n_grows_as_mde_shrinks():
    assert ab.required_n_per_arm(0.02, 0.10) > ab.required_n_per_arm(0.02, 0.20)


def test_required_n_rejects_impossible_rates():
    with pytest.raises(ValueError, match="in \\(0, 1\\)"):
        ab.required_n_per_arm(0.9, 0.20)  # lifted rate would be 1.08


def test_ztest_detects_an_obvious_difference():
    z, p = ab.two_proportion_ztest(500, 10_000, 700, 10_000)
    assert z > 0  # signed treatment minus control
    assert p < 0.001


def test_ztest_passes_an_obvious_null():
    _, p = ab.two_proportion_ztest(500, 10_000, 505, 10_000)
    assert p > 0.5


def test_srm_flags_a_52_48_split_at_a_million():
    _, p = ab.srm_check(520_000, 480_000)
    assert p < 1e-6


def test_srm_accepts_noise_at_ten_thousand():
    _, p = ab.srm_check(5_010, 4_990)
    assert p > 0.5


def test_synthetic_lift_is_deterministic_and_bounded():
    a = ab.apply_synthetic_lift(1_000, 50_000, 0.20, seed=42)
    b = ab.apply_synthetic_lift(1_000, 50_000, 0.20, seed=42)
    assert a == b
    assert 1_000 <= a <= 50_000
    # 200 expected extra converters; a seeded draw should land near that
    assert 100 <= a - 1_000 <= 300


def test_synthetic_lift_zero_adds_nothing():
    assert ab.apply_synthetic_lift(1_000, 50_000, 0.0, seed=42) == 1_000


def test_synthetic_lift_rejects_unreachable_lift():
    with pytest.raises(ValueError, match="unreachable"):
        ab.apply_synthetic_lift(9_000, 10_000, 0.5, seed=1)  # would need 4500 of 1000
