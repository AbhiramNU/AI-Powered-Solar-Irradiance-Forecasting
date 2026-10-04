"""
Raw data ingestion.

Downloads, per site:
- day-ahead NWP from each pinned model (Open-Meteo Previous Runs, ``_previous_day1``)
- ERA5 hourly GHI (the reference "actual")
- NASA POWER hourly GHI in UTC (independent cross-check only)

All sources are requested in UTC. Open-Meteo shifts data by whole hours when asked for a
timezone such as Asia/Kolkata (UTC+5:30), which mislabels every hourly mean by 30 minutes,
so local labels are derived later from the UTC interval end.

Each download is cached as parquet under ``data/raw/`` and recorded in
``data/raw/manifest.json``. There is no fallback: if a source cannot be fetched after
retries, ingestion fails and nothing downstream runs on partial or invented data.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

import pandas as pd
import requests

from src.config import RAW_DATA_DIR, RunConfig
from src.data.nasa_power import fetch_nasa_power_ghi
from src.data.open_meteo_era5 import fetch_era5_ghi
from src.data.open_meteo_previous_runs import fetch_previous_run

logger = logging.getLogger(__name__)

SUFFIX = "_previous_day1"
API_TIMEZONE = "GMT"


def utc_date_range(cfg: RunConfig) -> tuple[str, str]:
    """UTC calendar days covering the configured local date range (local days start before UTC days in IST)."""
    start = pd.Timestamp(f"{cfg.start_date} 00:00", tz=cfg.timezone).tz_convert("UTC") - pd.Timedelta(hours=1)
    end = pd.Timestamp(f"{cfg.end_date} 23:59", tz=cfg.timezone).tz_convert("UTC") + pd.Timedelta(hours=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def nwp_path(raw_dir: Path, site_id: str, model: str) -> Path:
    return raw_dir / "nwp" / f"{site_id}_{model}.parquet"


def era5_path(raw_dir: Path, site_id: str) -> Path:
    return raw_dir / "era5" / f"{site_id}.parquet"


def nasa_path(raw_dir: Path, site_id: str) -> Path:
    return raw_dir / "nasa_power" / f"{site_id}.parquet"


def with_retries(fn: Callable[[], pd.DataFrame], what: str, attempts: int = 3, backoff_s: float = 5.0) -> pd.DataFrame:
    """Retry transient network failures only. Data or parsing errors are raised immediately."""
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except requests.exceptions.RequestException as err:
            if attempt == attempts:
                raise RuntimeError(f"{what}: failed after {attempts} attempts: {err}") from err
            logger.warning(f"{what}: attempt {attempt}/{attempts} failed ({err}); retrying")
            time.sleep(backoff_s * attempt)
    raise AssertionError("unreachable")


def _write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def ingest_site(site: Dict[str, Any], cfg: RunConfig, raw_dir: Path = RAW_DATA_DIR, refresh: bool = False,
                include_nasa: bool = True) -> List[Dict[str, Any]]:
    """Fetch (or reuse cached) raw data for one site. Returns manifest entries."""
    sid, lat, lon = site["site_id"], site["latitude"], site["longitude"]
    entries: List[Dict[str, Any]] = []
    variables = cfg.nwp_required_variables + cfg.nwp_optional_variables
    start_utc, end_utc = utc_date_range(cfg)

    for prefix, model in cfg.nwp_models.items():
        path = nwp_path(raw_dir, sid, model)
        if path.exists() and not refresh:
            logger.info(f"[{sid}] NWP {model}: using cache {path.name}")
            continue
        df = with_retries(
            lambda: fetch_previous_run(
                lat, lon, start_utc, end_utc,
                variables=[v + SUFFIX for v in variables],
                model=model,
                required=[v + SUFFIX for v in cfg.nwp_required_variables],
                timezone=API_TIMEZONE,
            ),
            f"[{sid}] NWP {model}",
        )
        dropped = [c.removesuffix(SUFFIX) for c in df.attrs.get("dropped_all_null", [])]
        df = df.rename(columns={c: c.removesuffix(SUFFIX) for c in df.columns})
        _write(df, path)
        entries.append(_entry(path, "open-meteo-previous-runs", model, sid, df, dropped))

    path = era5_path(raw_dir, sid)
    if refresh or not path.exists():
        df = with_retries(
            lambda: fetch_era5_ghi(lat, lon, start_utc, end_utc, timezone=API_TIMEZONE, model=cfg.raw["truth"]["model"]),
            f"[{sid}] ERA5",
        )
        _write(df, path)
        entries.append(_entry(path, "open-meteo-archive", cfg.raw["truth"]["model"], sid, df, []))
    else:
        logger.info(f"[{sid}] ERA5: using cache {path.name}")

    if include_nasa:
        path = nasa_path(raw_dir, sid)
        if refresh or not path.exists():
            df = with_retries(
                lambda: fetch_nasa_power_ghi(lat, lon, start_utc, end_utc),
                f"[{sid}] NASA POWER",
            )
            _write(df, path)
            entries.append(_entry(path, "nasa-power", "SYN1DEG", sid, df, []))
        else:
            logger.info(f"[{sid}] NASA POWER: using cache {path.name}")

    return entries


def _entry(path: Path, source: str, model: str, site_id: str, df: pd.DataFrame, dropped: List[str]) -> Dict[str, Any]:
    return {
        "file": str(path.relative_to(path.parents[2])),
        "source": source,
        "model": model,
        "site_id": site_id,
        "rows": int(len(df)),
        "time_min": str(df["time"].min()),
        "time_max": str(df["time"].max()),
        "dropped_all_null_variables": dropped,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def ingest_all(sites: List[Dict[str, Any]], cfg: RunConfig, raw_dir: Path = RAW_DATA_DIR, refresh: bool = False,
               include_nasa: bool = True) -> Path:
    """Ingest all sites and merge new entries into ``manifest.json``."""
    manifest_path = raw_dir / "manifest.json"
    manifest: Dict[str, Dict[str, Any]] = {}
    if manifest_path.exists():
        manifest = {e["file"]: e for e in json.loads(manifest_path.read_text())["files"]}

    for site in sites:
        for entry in ingest_site(site, cfg, raw_dir, refresh=refresh, include_nasa=include_nasa):
            manifest[entry["file"]] = entry

    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"files": sorted(manifest.values(), key=lambda e: e["file"])}, indent=2))
    logger.info(f"Ingestion complete; manifest at {manifest_path}")
    return manifest_path
