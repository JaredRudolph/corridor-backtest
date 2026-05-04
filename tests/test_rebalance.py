import numpy as np
import pandas as pd
import pytest

from corridor_backtest.rebalance import (
    _bands,
    _breached,
    _on_schedule,
    apply_rebalance,
    should_rebalance,
)

# ---------------------------------------------------------------------------
# _bands
# ---------------------------------------------------------------------------


def test_bands_absolute():
    targets = np.array([0.40, 0.30, 0.30])
    lower, upper = _bands(targets, 0.05, "absolute")
    np.testing.assert_allclose(lower, [0.35, 0.25, 0.25])
    np.testing.assert_allclose(upper, [0.45, 0.35, 0.35])


def test_bands_relative():
    targets = np.array([0.40, 0.20])
    lower, upper = _bands(targets, 0.10, "relative")
    # 0.40 * (1 - 0.10) = 0.36, 0.40 * (1 + 0.10) = 0.44
    np.testing.assert_allclose(lower, [0.36, 0.18])
    np.testing.assert_allclose(upper, [0.44, 0.22])


def test_bands_unknown_type():
    with pytest.raises(ValueError, match="Unknown threshold_type"):
        _bands(np.array([0.5, 0.5]), 0.05, "bogus")


# ---------------------------------------------------------------------------
# _breached
# ---------------------------------------------------------------------------


def test_breached_within_absolute():
    targets = np.array([0.40, 0.60])
    weights = np.array([0.38, 0.62])  # 2% drift, band is 5%
    assert not _breached(weights, targets, 0.05, "absolute")


def test_breached_outside_absolute():
    targets = np.array([0.40, 0.60])
    weights = np.array([0.34, 0.66])  # 6% drift, band is 5%
    assert _breached(weights, targets, 0.05, "absolute")


def test_breached_within_relative():
    targets = np.array([0.25, 0.75])
    # relative band 10%: corridor for 0.25 is [0.225, 0.275]
    weights = np.array([0.26, 0.74])
    assert not _breached(weights, targets, 0.10, "relative")


def test_breached_outside_relative():
    targets = np.array([0.25, 0.75])
    # 0.25 * (1 - 0.10) = 0.225 lower bound; weight 0.22 breaches
    weights = np.array([0.22, 0.78])
    assert _breached(weights, targets, 0.10, "relative")


def test_breached_just_inside_band_edge():
    targets = np.array([0.40, 0.60])
    weights = np.array([0.36, 0.64])  # 1% inside the 5% absolute band
    assert not _breached(weights, targets, 0.05, "absolute")


# ---------------------------------------------------------------------------
# _on_schedule
# ---------------------------------------------------------------------------


def test_on_schedule_none_last_rebalance():
    date = pd.Timestamp("2023-01-15")
    assert _on_schedule(date, "M", None)
    assert _on_schedule(date, "Q", None)


def test_on_schedule_monthly_same_month():
    date = pd.Timestamp("2023-03-20")
    last = pd.Timestamp("2023-03-01")
    assert not _on_schedule(date, "M", last)


def test_on_schedule_monthly_new_month():
    date = pd.Timestamp("2023-04-01")
    last = pd.Timestamp("2023-03-31")
    assert _on_schedule(date, "M", last)


def test_on_schedule_quarterly_same_quarter():
    date = pd.Timestamp("2023-02-15")
    last = pd.Timestamp("2023-01-01")
    assert not _on_schedule(date, "Q", last)


def test_on_schedule_quarterly_new_quarter():
    date = pd.Timestamp("2023-04-01")
    last = pd.Timestamp("2023-03-31")
    assert _on_schedule(date, "Q", last)


def test_on_schedule_unknown_schedule():
    with pytest.raises(ValueError, match="Unknown schedule"):
        _on_schedule(pd.Timestamp("2023-01-01"), "W", pd.Timestamp("2022-12-01"))


# ---------------------------------------------------------------------------
# should_rebalance
# ---------------------------------------------------------------------------

DATE = pd.Timestamp("2023-04-03")
TARGETS = np.array([0.50, 0.50])
IN_BAND = np.array([0.48, 0.52])
OUT_OF_BAND = np.array([0.42, 0.58])  # 8% drift vs 5% band

BASE_CFG = {
    "band": 0.05,
    "threshold_type": "absolute",
    "schedule": "Q",
}


def test_mode_none_never_rebalances():
    cfg = {**BASE_CFG, "mode": "none"}
    do_it, trigger = should_rebalance(DATE, OUT_OF_BAND, TARGETS, cfg, None, True)
    assert not do_it
    assert trigger == ""


def test_mode_periodic_fires_on_schedule():
    cfg = {**BASE_CFG, "mode": "periodic"}
    last = pd.Timestamp("2022-12-15")  # different quarter
    do_it, trigger = should_rebalance(DATE, IN_BAND, TARGETS, cfg, last, False)
    assert do_it
    assert trigger == "periodic"


def test_mode_periodic_skips_off_schedule():
    cfg = {**BASE_CFG, "mode": "periodic"}
    last = pd.Timestamp("2023-04-01")  # same quarter
    do_it, trigger = should_rebalance(DATE, OUT_OF_BAND, TARGETS, cfg, last, True)
    assert not do_it


def test_mode_corridor_fires_when_breached():
    cfg = {**BASE_CFG, "mode": "corridor"}
    do_it, trigger = should_rebalance(DATE, OUT_OF_BAND, TARGETS, cfg, None, False)
    assert do_it
    assert trigger == "corridor"


def test_mode_corridor_silent_when_within():
    cfg = {**BASE_CFG, "mode": "corridor"}
    do_it, _ = should_rebalance(DATE, IN_BAND, TARGETS, cfg, None, False)
    assert not do_it


def test_mode_hybrid_fires_when_schedule_and_breach():
    cfg = {**BASE_CFG, "mode": "hybrid"}
    last = pd.Timestamp("2022-12-15")  # different quarter
    do_it, trigger = should_rebalance(DATE, IN_BAND, TARGETS, cfg, last, True)
    assert do_it
    assert trigger == "hybrid"


def test_mode_hybrid_silent_when_on_schedule_but_no_breach():
    cfg = {**BASE_CFG, "mode": "hybrid"}
    last = pd.Timestamp("2022-12-15")
    do_it, _ = should_rebalance(DATE, IN_BAND, TARGETS, cfg, last, False)
    assert not do_it


def test_mode_hybrid_silent_when_breach_but_off_schedule():
    cfg = {**BASE_CFG, "mode": "hybrid"}
    last = pd.Timestamp("2023-04-01")  # same quarter
    do_it, _ = should_rebalance(DATE, OUT_OF_BAND, TARGETS, cfg, last, True)
    assert not do_it


def test_should_rebalance_unknown_mode():
    cfg = {**BASE_CFG, "mode": "magic"}
    with pytest.raises(ValueError, match="Unknown rebalance mode"):
        should_rebalance(DATE, TARGETS, TARGETS, cfg, None, False)


# ---------------------------------------------------------------------------
# apply_rebalance
# ---------------------------------------------------------------------------


def _prices(values):
    return pd.Series(values, index=["A", "B"])


def test_apply_rebalance_to_target():
    cfg = {"rebalance_to": "target", "band": 0.05, "threshold_type": "absolute"}
    prices = _prices([100.0, 50.0])
    targets = np.array([0.60, 0.40])
    current = np.array([0.70, 0.30])
    portfolio_value = 1000.0

    shares, cost = apply_rebalance(portfolio_value, targets, prices, current, cfg)

    # No transaction cost configured -- cost should be zero and shares exact.
    assert cost == 0.0
    np.testing.assert_allclose(shares, [6.0, 8.0])


def test_apply_rebalance_to_band_edge_clips_breached():
    cfg = {"rebalance_to": "band_edge", "band": 0.05, "threshold_type": "absolute"}
    prices = _prices([100.0, 100.0])
    targets = np.array([0.50, 0.50])
    # A has drifted to 0.60 (above upper=0.55); B at 0.40 (below lower=0.45)
    current = np.array([0.60, 0.40])
    portfolio_value = 1000.0

    shares, cost = apply_rebalance(portfolio_value, targets, prices, current, cfg)
    final_weights = shares * prices.values / (portfolio_value - cost)

    # A clipped to 0.55, B clipped to 0.45; renormalized they stay 0.55/0.45
    np.testing.assert_allclose(final_weights.sum(), 1.0)
    assert final_weights[0] < 0.60  # moved toward target
    assert final_weights[1] > 0.40


def test_apply_rebalance_to_band_edge_leaves_within_unchanged():
    cfg = {"rebalance_to": "band_edge", "band": 0.10, "threshold_type": "absolute"}
    prices = _prices([100.0, 100.0])
    targets = np.array([0.50, 0.50])
    # Both within band -- weights stay as-is (modulo renorm which is no-op here)
    current = np.array([0.52, 0.48])
    portfolio_value = 1000.0

    shares, cost = apply_rebalance(portfolio_value, targets, prices, current, cfg)
    final_weights = shares * prices.values / (portfolio_value - cost)

    np.testing.assert_allclose(final_weights, current, atol=1e-10)


def test_apply_rebalance_unknown_rebalance_to():
    cfg = {"rebalance_to": "midpoint", "band": 0.05, "threshold_type": "absolute"}
    with pytest.raises(ValueError, match="Unknown rebalance_to"):
        apply_rebalance(
            1000.0,
            np.array([0.5, 0.5]),
            _prices([100.0, 100.0]),
            np.array([0.5, 0.5]),
            cfg,
        )
