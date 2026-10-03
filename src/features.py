"""
Feature engineering with an explicit issue-time availability check.

Every feature is registered with the data source it is computed from. Only sources that
exist when the day-ahead forecast is issued (NWP fields for the target day, solar
geometry, calendar, site identity) are allowed. Observations of the target, on the
target day or any other day, are never features; ``build_features`` raises if one is.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from src.config import RunConfig
from src.physics import clear_sky_index

ALLOWED_SOURCES = {"nwp", "geometry", "calendar", "site"}
OBSERVATION_COLUMNS = {"ghi_actual", "kt_actual", "ghi_persistence", "ghi_nasa"}

NWP_PASSTHROUGH = (
    "shortwave_radiation", "direct_radiation", "diffuse_radiation", "cloud_cover", "precipitation",
    "temperature_2m", "relative_humidity_2m", "dew_point_2m", "cape", "pressure_msl",
)


class LeakageError(ValueError):
    """Raised when a feature would use information unavailable at issue time."""


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    source: str
    description: str


def build_features(data: pd.DataFrame, cfg: RunConfig) -> Tuple[pd.DataFrame, List[FeatureSpec]]:
    """
    Add model features to the canonical table. Returns (frame, feature specs).

    Temporal context and daily summaries are computed within (site, local date), so a
    feature for day D only reads NWP values valid on day D.
    """
    d = data.sort_values(["site_id", "time_utc"]).copy()
    specs: List[FeatureSpec] = []
    daylight = d["is_daylight"].to_numpy()
    prefixes = list(cfg.nwp_models)
    primary = cfg.nwp_primary

    def add(name: str, values, source: str, description: str) -> None:
        d[name] = values
        specs.append(FeatureSpec(name, source, description))

    for p in prefixes:
        for var in NWP_PASSTHROUGH:
            col = f"{p}_{var}"
            if col in d.columns:
                specs.append(FeatureSpec(col, "nwp", f"{cfg.nwp_models[p]} day-ahead {var}"))
        add(f"{p}_kt", clear_sky_index(d[f"{p}_shortwave_radiation"], d["ghi_clearsky"], daylight),
            "nwp", f"{cfg.nwp_models[p]} clear-sky index")
        if f"{p}_diffuse_radiation" in d.columns:
            ghi = d[f"{p}_shortwave_radiation"]
            add(f"{p}_dif_frac", np.where(ghi > 10, d[f"{p}_diffuse_radiation"] / ghi.clip(lower=1), np.nan),
                "nwp", f"{cfg.nwp_models[p]} diffuse fraction")

    by_day = d.groupby(["site_id", "date"], sort=False)
    for k in (1, 2):
        for var, label in (("kt", "clear-sky index"), ("cloud_cover", "cloud cover")):
            col = f"{primary}_{var}"
            if col not in d.columns:
                continue
            add(f"{col}_m{k}", by_day[col].shift(k), "nwp", f"{label} {k} h earlier, same day")
            add(f"{col}_p{k}", by_day[col].shift(-k), "nwp", f"{label} {k} h later, same day")

    by_day = d.groupby(["site_id", "date"], sort=False)
    for p in prefixes:
        add(f"{p}_d_kt", by_day[f"{p}_kt"].transform("mean"), "nwp", f"{cfg.nwp_models[p]} daily mean clear-sky index")
    add(f"{primary}_d_kt_std", by_day[f"{primary}_kt"].transform("std"), "nwp", "primary NWP daily std of clear-sky index")
    if f"{primary}_cloud_cover" in d.columns:
        add(f"{primary}_d_cc", by_day[f"{primary}_cloud_cover"].transform("mean"), "nwp", "primary NWP daily mean cloud cover")
    if f"{primary}_precipitation" in d.columns:
        add(f"{primary}_d_precip", by_day[f"{primary}_precipitation"].transform("sum"), "nwp", "primary NWP daily precipitation")

    kts = d[[f"{p}_kt" for p in prefixes]]
    add("kt_mean", kts.mean(axis=1), "nwp", "mean clear-sky index across NWP models")
    add("kt_spread", kts.std(axis=1), "nwp", "spread of clear-sky index across NWP models")

    doy = d["time_local"].dt.dayofyear
    add("solar_elevation", d["solar_elevation"], "geometry", "solar elevation at interval midpoint")
    add("ghi_clearsky", d["ghi_clearsky"], "geometry", "Ineichen clear-sky GHI, interval mean")
    add("sin_doy", np.sin(2 * np.pi * doy / 365.25), "calendar", "day of year (sine)")
    add("cos_doy", np.cos(2 * np.pi * doy / 365.25), "calendar", "day of year (cosine)")
    add("hour_ist", d["hour_ist"], "calendar", "local hour (interval midpoint)")
    add("site_code", d["site_code"], "site", "site index")

    assert_issue_time_safe(specs)
    return d, specs


def assert_issue_time_safe(specs: List[FeatureSpec]) -> None:
    bad = [s.name for s in specs if s.source not in ALLOWED_SOURCES or s.name in OBSERVATION_COLUMNS]
    if bad:
        raise LeakageError(f"features not available at issue time: {bad}")
    names = [s.name for s in specs]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        raise ValueError(f"duplicate feature names: {dupes}")


def feature_names(specs: List[FeatureSpec]) -> List[str]:
    return [s.name for s in specs]


def daily_uncertainty(frame: pd.DataFrame, primary: str) -> pd.Series:
    """
    Day-level uncertainty from forecast inputs only: forecast cloudiness
    (1 - primary daily kt) plus disagreement between NWP models (daily mean kt spread).
    ``primary`` is the NWP prefix (e.g. ``ec``).
    """
    key = [frame["site_id"], frame["date"]]
    primary_kt = frame[f"{primary}_d_kt"]
    fallback = frame["kt_mean"].groupby(key).transform("mean")
    cloudiness = 1 - primary_kt.fillna(fallback)
    spread = frame["kt_spread"].groupby(key).transform("mean")
    return (cloudiness.fillna(0.5) + spread.fillna(0)).groupby(key).transform("first")


def describe_features(specs: List[FeatureSpec]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for s in specs:
        out.setdefault(s.source, []).append(s.name)
    return out
