"""
Quantile forecaster: LightGBM P10/P50/P90 with validation-year calibration.

Protocol (no test data touches any choice):
1. Fit each quantile on the train years, early-stopping on the validation years.
2. On out-of-sample validation predictions choose, per site: the P50 blend weight with
   raw primary NWP and the band multiplier that hits the coverage target on daylight hours;
   then the confidence thresholds and the daily-band multiplier.
3. Refit on train + validation with the early-stopped tree counts scaled up, keep every
   chosen constant, and save boosters as LightGBM text plus a JSON config.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

import lightgbm as lgb
import numpy as np
import pandas as pd

from src.config import RunConfig
from src.features import daily_uncertainty

logger = logging.getLogger(__name__)

CONFIDENCE_LABELS = ("High", "Medium", "Low")


@dataclass
class ForecasterConfig:
    features: List[str]
    quantiles: Dict[str, float]
    primary_prefix: str
    primary_ghi: str
    blend_weight: Dict[str, float]
    band_multiplier: Dict[str, float]
    daily_band_multiplier: float
    confidence_thresholds: Tuple[float, float]
    trees: Dict[str, int]
    params: Dict[str, Any]
    selection: Dict[str, Any] = field(default_factory=dict)


class QuantileForecaster:
    def __init__(self, config: ForecasterConfig, boosters: Dict[str, lgb.Booster]):
        self.config = config
        self.boosters = boosters

    # ---------- prediction ----------

    def raw_quantiles(self, frame: pd.DataFrame) -> Dict[str, np.ndarray]:
        X = frame[self.config.features]
        return {k: np.clip(b.predict(X), 0, None) for k, b in self.boosters.items()}

    def predict(self, frame: pd.DataFrame, daylight_col: str = "is_daylight") -> pd.DataFrame:
        """Calibrated P10/P50/P90 for every row (0 outside daylight) and a day-level confidence label."""
        cfg = self.config
        out = pd.DataFrame(index=frame.index, data={"ghi_p10": 0.0, "ghi_p50": 0.0, "ghi_p90": 0.0})
        day = frame[frame[daylight_col]]
        if len(day):
            raw = self.raw_quantiles(day)
            p50 = blend(raw["p50"], day[cfg.primary_ghi].to_numpy(), _per_row(day, cfg.blend_weight))
            lo, hi = band(raw["p10"], p50, raw["p90"], _per_row(day, cfg.band_multiplier), day["ghi_clearsky"].to_numpy())
            out.loc[day.index, "ghi_p10"] = lo
            out.loc[day.index, "ghi_p50"] = p50
            out.loc[day.index, "ghi_p90"] = hi
        out["confidence"] = confidence_label(daily_uncertainty(frame, cfg.primary_prefix), cfg.confidence_thresholds)
        return out

    # ---------- persistence ----------

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        for k, b in self.boosters.items():
            b.save_model(str(directory / f"lgbm_{k}.txt"))
        (directory / "forecaster.json").write_text(json.dumps(asdict(self.config), indent=2, default=_json_default))

    @classmethod
    def load(cls, directory: Path) -> "QuantileForecaster":
        raw = json.loads((directory / "forecaster.json").read_text())
        raw["confidence_thresholds"] = tuple(raw["confidence_thresholds"])
        config = ForecasterConfig(**raw)
        boosters = {k: lgb.Booster(model_file=str(directory / f"lgbm_{k}.txt")) for k in config.quantiles}
        return cls(config, boosters)


# ---------- building blocks ----------

def _json_default(o: Any) -> Any:
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    raise TypeError(f"not JSON serialisable: {type(o)}")


def _per_row(frame: pd.DataFrame, per_site: Dict[str, float]) -> np.ndarray:
    if "*" in per_site:
        return np.full(len(frame), per_site["*"])
    return frame["site_id"].map(per_site).to_numpy(dtype=float)


def blend(p50_model: np.ndarray, nwp: np.ndarray, weight: np.ndarray | float) -> np.ndarray:
    """w * model + (1 - w) * raw NWP; model only where NWP is missing."""
    w = np.broadcast_to(np.asarray(weight, dtype=float), p50_model.shape)
    nwp = np.asarray(nwp, dtype=float)
    return np.where(np.isnan(nwp), p50_model, w * p50_model + (1 - w) * np.nan_to_num(nwp))


def band(p10: np.ndarray, p50: np.ndarray, p90: np.ndarray, k: np.ndarray | float, clearsky: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Scale the raw quantile spread around P50 by k; enforce 0 <= P10 <= P50 <= P90 <= max(1.25 * clear-sky, P50)."""
    lo = np.clip(p50 - k * np.maximum(p50 - p10, 0), 0, None)
    hi = np.minimum(p50 + k * np.maximum(p90 - p50, 0), np.maximum(clearsky * 1.25, p50))
    return np.minimum(lo, p50), np.maximum(hi, p50)


def coverage_pct(actual: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    ok = ~np.isnan(actual)
    return float(np.mean((actual[ok] >= lo[ok]) & (actual[ok] <= hi[ok])) * 100)


def confidence_label(u: pd.Series, thresholds: Tuple[float, float]) -> np.ndarray:
    u = u.to_numpy(dtype=float)
    labels = np.where(u <= thresholds[0], "High", np.where(u <= thresholds[1], "Medium", "Low"))
    return np.where(np.isnan(u), "Medium", labels)


def _fit_booster(alpha: float, X: pd.DataFrame, y: pd.Series, params: Dict[str, Any], n_estimators: int,
                 valid: Tuple[pd.DataFrame, pd.Series] | None, early_stopping_rounds: int) -> Tuple[lgb.Booster, int]:
    model = lgb.LGBMRegressor(objective="quantile", alpha=alpha, **{**params, "n_estimators": n_estimators})
    if valid is None:
        model.fit(X, y)
        return model.booster_, n_estimators
    model.fit(X, y, eval_X=(valid[0],), eval_y=(valid[1],), eval_metric="quantile",
              callbacks=[lgb.early_stopping(early_stopping_rounds, verbose=False)])
    return model.booster_, int(model.best_iteration_ or n_estimators)


def _choose(grid: List[float], score) -> float:
    scores = [score(v) for v in grid]
    return float(grid[int(np.nanargmin(scores))])


def daily_totals(frame: pd.DataFrame, k_daily: float) -> pd.DataFrame:
    """
    Daily irradiation (kWh/m²) per site-day from hourly forecasts.

    Daily P50 is the sum of hourly P50. Summing hourly P10/P90 would assume errors move in
    lockstep across hours and overstate the daily range, so the summed half-widths are
    scaled by ``k_daily`` (calibrated on validation days to the coverage target).
    """
    f = frame.assign(
        _lo=frame["ghi_p50"] - frame["ghi_p10"],
        _hi=frame["ghi_p90"] - frame["ghi_p50"],
        _actual_missing=frame["is_daylight"] & frame["ghi_actual"].isna(),
    )
    g = f.groupby(["site_id", "date"], sort=True)
    daily = g.agg(
        split=("split", "first"),
        confidence=("confidence", "first"),
        actual=("ghi_actual", "sum"),
        actual_missing=("_actual_missing", "any"),
        p50=("ghi_p50", "sum"),
        lo=("_lo", "sum"),
        hi=("_hi", "sum"),
        nwp=("ghi_nwp", "sum"),
        nwp_missing=("ghi_nwp", lambda s: bool(s.isna().any())),
        persistence=("ghi_persistence", "sum"),
        persistence_missing=("ghi_persistence", lambda s: bool(s.isna().any())),
        clearsky=("ghi_clearsky", "sum"),
    ).reset_index()
    to_kwh = 1 / 1000.0  # sum of hourly mean W/m² over 1 h steps = Wh/m²
    out = pd.DataFrame({
        "site_id": daily["site_id"],
        "date": daily["date"],
        "split": daily["split"],
        "confidence": daily["confidence"],
        "actual_kwh_m2": np.where(daily["actual_missing"], np.nan, daily["actual"] * to_kwh),
        "p10_kwh_m2": np.clip(daily["p50"] - k_daily * daily["lo"], 0, None) * to_kwh,
        "p50_kwh_m2": daily["p50"] * to_kwh,
        "p90_kwh_m2": (daily["p50"] + k_daily * daily["hi"]) * to_kwh,
        "nwp_kwh_m2": np.where(daily["nwp_missing"], np.nan, daily["nwp"] * to_kwh),
        "persistence_kwh_m2": np.where(daily["persistence_missing"], np.nan, daily["persistence"] * to_kwh),
        "clearsky_kwh_m2": daily["clearsky"] * to_kwh,
    })
    return out


def fit_forecaster(frame: pd.DataFrame, features: List[str], cfg: RunConfig) -> QuantileForecaster:
    """Run the full train → calibrate → refit protocol. ``frame`` needs features, target and split."""
    primary = f"{cfg.nwp_primary}_shortwave_radiation"
    usable = frame["is_daylight"] & frame["ghi_actual"].notna()
    train = frame[usable & (frame["split"] == "train")]
    valid = frame[usable & (frame["split"] == "validation")]
    if train.empty or valid.empty:
        raise ValueError("train and validation splits must both contain daylight rows with targets")
    logger.info(f"Training rows: {len(train):,}; validation rows: {len(valid):,}")

    params = cfg.model_params
    n_max = int(params.get("n_estimators", 5000))
    boosters, best_iters, vp = {}, {}, {}
    for k, alpha in cfg.quantiles.items():
        b, it = _fit_booster(alpha, train[features], train["ghi_actual"], params, n_max,
                             (valid[features], valid["ghi_actual"]), cfg.early_stopping_rounds)
        boosters[k], best_iters[k] = b, it
        vp[k] = np.clip(b.predict(valid[features], num_iteration=it), 0, None)
        logger.info(f"  {k}: {it} trees (early-stopped on validation)")

    y = valid["ghi_actual"].to_numpy()
    nwp = valid[primary].to_numpy()
    cs = valid["ghi_clearsky"].to_numpy()
    sites = valid["site_id"].to_numpy()
    groups = sorted(set(sites)) if cfg.per_site_calibration else ["*"]
    target = cfg.coverage_target_pct

    weights, mults, selection = {}, {}, {"validation_mae": {}, "validation_coverage": {}}
    p50_valid = np.empty_like(y)
    lo_valid, hi_valid = np.empty_like(y), np.empty_like(y)
    for g in groups:
        m = np.ones(len(y), bool) if g == "*" else sites == g
        w = _choose(cfg.blend_weight_grid, lambda w: np.mean(np.abs(blend(vp["p50"][m], nwp[m], w) - y[m])))
        p50 = blend(vp["p50"][m], nwp[m], w)
        kk = _choose(cfg.band_multiplier_grid,
                     lambda kk: abs(coverage_pct(y[m], *band(vp["p10"][m], p50, vp["p90"][m], kk, cs[m])) - target))
        lo, hi = band(vp["p10"][m], p50, vp["p90"][m], kk, cs[m])
        weights[g], mults[g] = w, kk
        p50_valid[m], lo_valid[m], hi_valid[m] = p50, lo, hi
        selection["validation_mae"][g] = round(float(np.mean(np.abs(p50 - y[m]))), 3)
        selection["validation_coverage"][g] = round(coverage_pct(y[m], lo, hi), 2)
        logger.info(f"  calibration [{g}]: blend weight {w:.2f}, band multiplier {kk:.2f}")
    selection["validation_mae_raw_nwp"] = round(float(np.nanmean(np.abs(nwp - y))), 3)

    # Confidence thresholds: terciles of validation-day uncertainty.
    u_valid = daily_uncertainty(valid, cfg.nwp_primary).groupby([valid["site_id"], valid["date"]]).first()
    thresholds = (float(u_valid.quantile(1 / 3)), float(u_valid.quantile(2 / 3)))

    # Daily band multiplier on validation days (complete daylight coverage only).
    vday = frame[(frame["split"] == "validation")].copy()
    vday[["ghi_p10", "ghi_p50", "ghi_p90"]] = 0.0
    vday.loc[valid.index, "ghi_p10"] = lo_valid
    vday.loc[valid.index, "ghi_p50"] = p50_valid
    vday.loc[valid.index, "ghi_p90"] = hi_valid
    vday["confidence"] = "Medium"
    vday["ghi_nwp"] = vday[primary]
    base = daily_totals(vday, 1.0)
    ok = base["actual_kwh_m2"].notna()

    def daily_cov(kd: float) -> float:
        lo_d = np.clip(base["p50_kwh_m2"] - kd * (base["p50_kwh_m2"] - base["p10_kwh_m2"]), 0, None)
        hi_d = base["p50_kwh_m2"] + kd * (base["p90_kwh_m2"] - base["p50_kwh_m2"])
        a = base["actual_kwh_m2"]
        return float(((a >= lo_d) & (a <= hi_d))[ok].mean() * 100)

    k_daily = _choose([round(x, 3) for x in np.linspace(0.05, 1.5, 146)], lambda kd: abs(daily_cov(kd) - target))
    selection["validation_daily_coverage"] = round(daily_cov(k_daily), 2)
    logger.info(f"  daily band multiplier {k_daily:.2f}; confidence thresholds {np.round(thresholds, 3).tolist()}")

    # Refit on train + validation.
    full = frame[usable & frame["split"].isin(["train", "validation"])]
    trees = {k: max(1, int(round(best_iters[k] * cfg.refit_tree_scale))) for k in cfg.quantiles}
    final = {}
    for k, alpha in cfg.quantiles.items():
        final[k], _ = _fit_booster(alpha, full[features], full["ghi_actual"], params, trees[k], None, 0)
    logger.info(f"Refit on {len(full):,} rows with trees {trees}")

    config = ForecasterConfig(
        features=list(features),
        quantiles=dict(cfg.quantiles),
        primary_prefix=cfg.nwp_primary,
        primary_ghi=primary,
        blend_weight=weights,
        band_multiplier=mults,
        daily_band_multiplier=k_daily,
        confidence_thresholds=thresholds,
        trees=trees,
        params=dict(params),
        selection=selection,
    )
    return QuantileForecaster(config, final)
