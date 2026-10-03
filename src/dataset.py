"""
Canonical hourly dataset.

Joins raw ERA5 (target) and pinned NWP models onto one regular hourly grid per site,
keyed by the UTC END of each averaging hour (``time_utc``). In IST (UTC+5:30) each
interval runs from hh-1:30 to hh:30, so its midpoint falls on the hour; ``date`` and
``hour_ist`` label that midpoint. The grid
adds solar geometry and the idealised persistence reference, and records data-quality
statistics. Missing values stay NaN: physical inputs are never imputed with zeros, and
quality gates raise ``DataQualityError`` instead of silently degrading the data.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from src.config import RAW_DATA_DIR, RunConfig
from src.data.validation import DataQualityError
from src.ingest import era5_path, nwp_path
from src.physics import clear_sky_index, hourly_solar_geometry

logger = logging.getLogger(__name__)

RADIATION_VARS = ("shortwave_radiation", "direct_radiation", "diffuse_radiation")
HALF_HOUR = pd.Timedelta(minutes=30)


def hourly_grid(cfg: RunConfig) -> pd.DatetimeIndex:
    """UTC interval ends whose local midpoints cover every hour of the configured local dates."""
    centres = pd.date_range(f"{cfg.start_date} 00:00", f"{cfg.end_date} 23:00", freq="h", tz=cfg.timezone)
    ends = (centres + HALF_HOUR).tz_convert("UTC")
    if not (ends.minute == 0).all():
        raise ValueError(f"timezone {cfg.timezone} does not put UTC hourly intervals' midpoints on the local hour")
    return ends


def _load_on_grid(path: Path, grid: pd.DatetimeIndex) -> Tuple[pd.DataFrame, Dict[str, int]]:
    if not path.exists():
        raise FileNotFoundError(f"Raw file missing: {path}. Run `python -m src.pipeline ingest` first.")
    df = pd.read_parquet(path)
    times = pd.DatetimeIndex(df["time"])
    if times.tz is None:
        raise DataQualityError(f"{path.name}: timestamps are not timezone-aware; re-run ingestion")
    times = times.tz_convert("UTC")
    df = df.drop(columns="time").set_index(times)
    dupes = int(df.index.duplicated().sum())
    df = df[~df.index.duplicated(keep="first")]
    off_grid = int((~df.index.isin(grid)).sum())
    out = df.reindex(grid)
    stats = {"duplicate_timestamps": dupes, "off_grid_timestamps": off_grid,
             "missing_timestamps": int((~grid.isin(df.index)).sum())}
    return out, stats


def build_site_frame(site: Dict[str, Any], cfg: RunConfig, raw_dir: Path = RAW_DATA_DIR) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    sid = site["site_id"]
    grid = hourly_grid(cfg)
    qc: Dict[str, Any] = {"site_id": sid, "sources": {}}

    era5, stats = _load_on_grid(era5_path(raw_dir, sid), grid)
    ghi = era5["shortwave_radiation"].astype(float)
    stats["negative_values_clipped"] = int((ghi < 0).sum())
    frame = pd.DataFrame({"ghi_actual": ghi.clip(lower=0)}, index=grid)
    qc["sources"]["era5"] = stats

    for prefix, model in cfg.nwp_models.items():
        nwp, stats = _load_on_grid(nwp_path(raw_dir, sid, model), grid)
        for var in cfg.nwp_required_variables:
            if var not in nwp.columns:
                raise DataQualityError(f"[{sid}] {model}: required variable '{var}' absent from raw file")
        stats["variables"] = sorted(nwp.columns)
        stats["absent_optional_variables"] = sorted(set(cfg.nwp_optional_variables) - set(nwp.columns))
        neg = 0
        for var in nwp.columns:
            col = nwp[var].astype(float)
            if var in RADIATION_VARS:
                neg += int((col < 0).sum())
                col = col.clip(lower=0)
            frame[f"{prefix}_{var}"] = col
        stats["negative_values_clipped"] = neg
        qc["sources"][model] = stats

    geo = hourly_solar_geometry(grid, site, substeps=cfg.clearsky_substeps_per_hour)
    geo.index = grid
    frame = frame.join(geo)
    frame["is_daylight"] = frame["ghi_clearsky"] > cfg.daylight_clearsky_wm2

    frame["kt_actual"] = clear_sky_index(frame["ghi_actual"], frame["ghi_clearsky"], frame["is_daylight"].to_numpy())

    # Idealised persistence: yesterday's clear-sky index at the same hour applied to today's clear sky.
    # ERA5 is published with ~5 days' delay, so this is NOT available at issue time; it is an optimistic reference.
    prev_actual = frame["ghi_actual"].shift(24, freq="h").reindex(grid)
    prev_kt = frame["kt_actual"].shift(24, freq="h").reindex(grid)
    persistence = np.where(prev_kt.notna(), prev_kt * frame["ghi_clearsky"], prev_actual)
    frame["ghi_persistence"] = np.where(frame["is_daylight"], persistence, 0.0)
    frame.loc[prev_actual.isna(), "ghi_persistence"] = np.nan

    frame.index.name = "time_utc"
    frame = frame.reset_index()
    frame["time_local"] = (frame["time_utc"] - HALF_HOUR).dt.tz_convert(cfg.timezone)
    frame["site_id"] = sid
    frame["date"] = frame["time_local"].dt.strftime("%Y-%m-%d")
    frame["hour_ist"] = frame["time_local"].dt.hour.astype("int64")
    frame["year"] = frame["time_local"].dt.year
    frame["split"] = frame["year"].map(cfg.split_of_year)

    qc["null_fraction_daylight"] = _null_fractions(frame, cfg)
    return frame, qc


def _null_fractions(frame: pd.DataFrame, cfg: RunConfig) -> Dict[str, Dict[str, float]]:
    day = frame[frame["is_daylight"]]
    cols = ["ghi_actual"] + [c for c in frame.columns if c.split("_", 1)[0] in cfg.nwp_models]
    out = {}
    for year, g in day.groupby("year"):
        out[str(year)] = {c: round(float(g[c].isna().mean()), 4) for c in cols}
    return out


def build_dataset(sites: List[Dict[str, Any]], cfg: RunConfig, raw_dir: Path = RAW_DATA_DIR) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Canonical hourly table for all sites plus QC report. Raises DataQualityError on failed gates."""
    frames, qc_sites = [], []
    for code, site in enumerate(sites):
        f, qc = build_site_frame(site, cfg, raw_dir)
        f["site_code"] = code
        frames.append(f)
        qc_sites.append(qc)
        logger.info(f"[{site['site_id']}] canonical rows: {len(f):,}, daylight: {int(f.is_daylight.sum()):,}")
    data = pd.concat(frames, ignore_index=True)

    gates = check_quality_gates(data, cfg)
    return data, {"sites": qc_sites, "gates": gates}


def check_quality_gates(data: pd.DataFrame, cfg: RunConfig) -> Dict[str, Any]:
    day = data[data["is_daylight"]]
    target_null = float(day["ghi_actual"].isna().mean())
    primary = f"{cfg.nwp_primary}_shortwave_radiation"
    test_day = day[day["split"] == "test"]
    primary_null_test = float(test_day[primary].isna().mean()) if len(test_day) else 1.0
    gates = {
        "target_null_fraction_daylight": round(target_null, 4),
        "target_null_limit": cfg.max_target_null_fraction,
        "primary_ghi_null_fraction_test_daylight": round(primary_null_test, 4),
        "primary_ghi_null_limit": cfg.max_primary_ghi_null_fraction_test,
    }
    if target_null > cfg.max_target_null_fraction:
        raise DataQualityError(f"ERA5 target missing on {target_null:.1%} of daylight hours (limit {cfg.max_target_null_fraction:.1%})")
    if primary_null_test > cfg.max_primary_ghi_null_fraction_test:
        raise DataQualityError(
            f"Primary NWP GHI missing on {primary_null_test:.1%} of test daylight hours (limit {cfg.max_primary_ghi_null_fraction_test:.1%})")
    return gates
