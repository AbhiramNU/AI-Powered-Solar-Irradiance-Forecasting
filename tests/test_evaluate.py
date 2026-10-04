"""Metric definitions and evaluation conventions."""

import numpy as np
import pandas as pd
import pytest

from src.evaluate import bootstrap_skill_interval, pinball_loss, point_metrics
from src.model import band, blend, coverage_pct


def test_point_metrics_known_values():
    m = point_metrics(np.array([100.0, 200.0, 300.0]), np.array([110.0, 190.0, 330.0]), baseline=np.array([150.0, 150.0, 350.0]))
    assert m["mae"] == pytest.approx(50 / 3, abs=0.01)
    assert m["bias"] == pytest.approx(10.0)
    assert m["rmse"] == pytest.approx(np.sqrt((100 + 100 + 900) / 3), abs=0.01)
    assert m["nrmse"] == pytest.approx(m["rmse"] / 200 * 100, abs=0.01)
    assert m["skill"] == pytest.approx((1 - (50 / 3) / 50) * 100, abs=0.01)


def test_point_metrics_ignore_missing_rows():
    m = point_metrics(np.array([100.0, np.nan]), np.array([110.0, 5.0]))
    assert m["mae"] == 10.0


def test_pinball_loss():
    assert pinball_loss(np.array([10.0]), np.array([0.0]), 0.9) == pytest.approx(9.0)
    assert pinball_loss(np.array([0.0]), np.array([10.0]), 0.9) == pytest.approx(1.0)


def test_night_rows_inflate_coverage_which_is_why_metrics_exclude_them():
    actual = np.array([0, 0, 0, 0, 500.0, 600.0])
    lo = np.array([0, 0, 0, 0, 510.0, 610.0])
    hi = np.array([0, 0, 0, 0, 520.0, 620.0])
    assert coverage_pct(actual, lo, hi) == pytest.approx(4 / 6 * 100)
    assert coverage_pct(actual[4:], lo[4:], hi[4:]) == 0.0


def test_bootstrap_interval_contains_point_skill_and_is_deterministic():
    rng = np.random.default_rng(0)
    n = 24 * 60
    actual = rng.uniform(0, 800, n)
    frame = pd.DataFrame({
        "date": np.repeat([f"2026-01-{d:02d}" if d < 32 else f"2026-02-{d - 31:02d}" for d in range(1, 61)], 24),
        "ghi_actual": actual,
        "p": actual + rng.normal(0, 30, n),
        "b": actual + rng.normal(0, 60, n),
    })
    a = bootstrap_skill_interval(frame, "p", "b", 200, 3, 0.95)
    b = bootstrap_skill_interval(frame, "p", "b", 200, 3, 0.95)
    point = point_metrics(frame.ghi_actual, frame.p, frame.b)["skill"]
    assert a == b
    assert a["low"] <= point <= a["high"]


def test_band_and_blend_keep_quantiles_ordered():
    p10, p50, p90 = np.array([80.0, 300.0]), np.array([100.0, 250.0]), np.array([90.0, 400.0])
    lo, hi = band(p10, p50, p90, 1.5, np.array([200.0, 800.0]))
    assert (lo <= p50).all() and (p50 <= hi).all() and (lo >= 0).all()
    assert blend(np.array([100.0, 100.0]), np.array([200.0, np.nan]), 0.75).tolist() == [125.0, 100.0]
