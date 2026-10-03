"""
Forecast evaluation.

Headline metrics use daylight hours only: at night every model is trivially exact, and
including those hours roughly halves MAE and inflates band coverage. All-hours figures
are kept in a separate block for comparison with earlier reports. Skill figures carry a
bootstrap interval that resamples whole days (all sites together, since sites share weather).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.contract import CONFIDENCE_LEVELS, CONTRACT_VERSION
from src.model import coverage_pct

MODEL_COLUMNS = {"ml_model_p50": "ghi_p50", "raw_nwp": "ghi_nwp", "persistence": "ghi_persistence"}
SKILL_BASELINE = {"ml_model_p50": "ghi_nwp", "raw_nwp": "ghi_persistence", "persistence": None}


def _r(x: float, nd: int = 2) -> float:
    return round(float(x), nd)


def point_metrics(actual: np.ndarray, pred: np.ndarray, baseline: Optional[np.ndarray] = None) -> Dict[str, float]:
    """MAE, RMSE, nRMSE (% of mean actual), bias (pred - actual), skill (% MAE reduction vs baseline)."""
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    ok = ~(np.isnan(actual) | np.isnan(pred))
    if baseline is not None:
        baseline = np.asarray(baseline, dtype=float)
        ok &= ~np.isnan(baseline)
    if not ok.any():
        raise ValueError("no rows with both actual and prediction")
    a, p = actual[ok], pred[ok]
    err = p - a
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mean_a = float(np.mean(a))
    out = {
        "mae": _r(mae),
        "rmse": _r(rmse),
        "nrmse": _r(rmse / mean_a * 100) if mean_a > 0 else 0.0,
        "bias": _r(np.mean(err)),
        "skill": 0.0,
    }
    if baseline is not None:
        base_mae = float(np.mean(np.abs(baseline[ok] - a)))
        out["skill"] = _r((1 - mae / base_mae) * 100) if base_mae > 0 else 0.0
    return out


def pinball_loss(actual: np.ndarray, pred: np.ndarray, alpha: float) -> float:
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    ok = ~np.isnan(actual)
    diff = actual[ok] - pred[ok]
    return float(np.mean(np.maximum(alpha * diff, (alpha - 1) * diff)))


def bootstrap_skill_interval(frame: pd.DataFrame, pred: str, base: str, n: int, seed: int, level: float) -> Dict[str, float]:
    """Percentile interval on MAE skill (%) resampling dates with replacement."""
    f = frame.dropna(subset=["ghi_actual", pred, base])
    per_day = f.assign(
        e_pred=(f[pred] - f["ghi_actual"]).abs(),
        e_base=(f[base] - f["ghi_actual"]).abs(),
    ).groupby("date")[["e_pred", "e_base"]].sum()
    if per_day.empty:
        return {"low": 0.0, "high": 0.0, "level": level}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(per_day), size=(n, len(per_day)))
    ep = per_day["e_pred"].to_numpy()[idx].sum(axis=1)
    eb = per_day["e_base"].to_numpy()[idx].sum(axis=1)
    skill = (1 - ep / eb) * 100
    tail = (1 - level) / 2 * 100
    return {"low": _r(np.percentile(skill, tail)), "high": _r(np.percentile(skill, 100 - tail)), "level": level}


def _models_block(frame: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    out = {}
    for key, col in MODEL_COLUMNS.items():
        base = SKILL_BASELINE[key]
        out[key] = point_metrics(frame["ghi_actual"], frame[col], None if base is None else frame[base])
    return out


def _mae(frame: pd.DataFrame, col: str) -> Optional[float]:
    f = frame.dropna(subset=["ghi_actual", col])
    return _r(np.mean(np.abs(f[col] - f["ghi_actual"]))) if len(f) else None


def independent_check(test: pd.DataFrame, reference: pd.Series, name: str) -> Optional[Dict[str, Any]]:
    """
    Score forecasts against a second reference that neither the model nor its NWP input was fitted to.

    A model trained on ERA5 can gain skill partly by learning ERA5's own systematic differences from the
    NWP input. If that gain disappears against an independent reference, it reflects the target, not the sky.
    """
    f = test.assign(_ref=reference)
    f = f[f["is_daylight"] & f["_ref"].notna() & f["ghi_actual"].notna() & f["ghi_nwp"].notna()]
    if f.empty:
        return None
    ref = f["_ref"]
    return {
        "reference": name,
        "rows": int(len(f)),
        "ml_model_p50": point_metrics(ref, f["ghi_p50"], f["ghi_nwp"]),
        "raw_nwp": point_metrics(ref, f["ghi_nwp"]),
        "era5": point_metrics(ref, f["ghi_actual"]),
    }


def evaluate(test: pd.DataFrame, daily: pd.DataFrame, sites: List[Dict[str, Any]], *, run_id: str, model_version: str,
             quantiles: Dict[str, float], n_boot: int, seed: int, level: float,
             independent: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build metrics.json content from test-split hourly and daily forecasts."""
    if not (test["split"] == "test").all():
        raise ValueError("evaluate() must only receive test-split rows")
    day = test[test["is_daylight"] & test["ghi_actual"].notna()]

    overall: Dict[str, Any] = _models_block(day)
    overall["p10_p90_coverage"] = _r(coverage_pct(day["ghi_actual"].to_numpy(), day["ghi_p10"].to_numpy(), day["ghi_p90"].to_numpy()))
    overall["quantile_crossings"] = int(((test.ghi_p10 > test.ghi_p50) | (test.ghi_p50 > test.ghi_p90)).sum())
    overall["pinball"] = {k: _r(pinball_loss(day["ghi_actual"], day[f"ghi_{k}"], a)) for k, a in quantiles.items()}
    overall["skill_interval"] = {
        "vs_raw_nwp": bootstrap_skill_interval(day, "ghi_p50", "ghi_nwp", n_boot, seed, level),
        "vs_persistence": bootstrap_skill_interval(day, "ghi_p50", "ghi_persistence", n_boot, seed, level),
    }
    overall["rows"] = int(len(day))

    all_rows = test[test["ghi_actual"].notna()]
    all_hours: Dict[str, Any] = _models_block(all_rows)
    all_hours["p10_p90_coverage"] = _r(coverage_pct(all_rows["ghi_actual"].to_numpy(), all_rows["ghi_p10"].to_numpy(), all_rows["ghi_p90"].to_numpy()))

    d_ok = daily.dropna(subset=["actual_kwh_m2"])
    daily_block = {
        "unit": "kWh/m²",
        "ml_model_p50": point_metrics(d_ok["actual_kwh_m2"], d_ok["p50_kwh_m2"], d_ok["nwp_kwh_m2"]),
        "raw_nwp": point_metrics(d_ok["actual_kwh_m2"], d_ok["nwp_kwh_m2"], d_ok["persistence_kwh_m2"]),
        "p10_p90_coverage": _r(coverage_pct(d_ok["actual_kwh_m2"].to_numpy(), d_ok["p10_kwh_m2"].to_numpy(), d_ok["p90_kwh_m2"].to_numpy())),
        "days": int(len(d_ok)),
    }

    by_site: Dict[str, Any] = {}
    for s in sites:
        sd = day[day["site_id"] == s["site_id"]]
        block: Dict[str, Any] = {"name": s["name"], "climate_zone": s["climate_zone"], **_models_block(sd)}
        block["coverage"] = _r(coverage_pct(sd["ghi_actual"].to_numpy(), sd["ghi_p10"].to_numpy(), sd["ghi_p90"].to_numpy()))
        block["skill_interval"] = {"vs_raw_nwp": bootstrap_skill_interval(sd, "ghi_p50", "ghi_nwp", n_boot, seed, level)}
        by_site[s["site_id"]] = block

    by_month: Dict[str, Any] = {}
    day_m = day.assign(month=day["date"].str[:7])
    for month, md in day_m.groupby("month", sort=True):
        by_month[month] = {
            "overall": {k: _mae(md, c) for k, c in MODEL_COLUMNS.items()},
            "by_site": {sid: _mae(g, "ghi_p50") for sid, g in md.groupby("site_id")},
        }

    by_conf: Dict[str, Any] = {}
    for level_name in CONFIDENCE_LEVELS:
        cd = day[day["confidence"] == level_name]
        if len(cd):
            by_conf[level_name] = {
                "site_days": int(cd[["site_id", "date"]].drop_duplicates().shape[0]),
                "mae": _mae(cd, "ghi_p50"),
                "coverage": _r(coverage_pct(cd["ghi_actual"].to_numpy(), cd["ghi_p10"].to_numpy(), cd["ghi_p90"].to_numpy())),
            }

    return {
        "contract_version": CONTRACT_VERSION,
        "model_version": model_version,
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "test_period": {"start": str(test["date"].min()), "end": str(test["date"].max())},
        "convention": ("Headline metrics use daylight hours (interval-mean clear-sky GHI above the daylight threshold) "
                       "of the test split, scored against ERA5. `skill` is the % reduction in MAE: ML vs raw NWP, raw NWP "
                       "vs persistence. Persistence is idealised (uses yesterday's ERA5, which is not available at issue time)."),
        "overall": overall,
        "all_hours": all_hours,
        "daily": daily_block,
        "by_site": by_site,
        "by_month": by_month,
        "by_confidence": by_conf,
        "independent_check": independent,
    }
