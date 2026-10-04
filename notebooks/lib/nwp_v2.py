"""Day-ahead NWP download helpers for the v2 (leak-free) model notebook.

Pins specific weather models instead of Open-Meteo's `best_match`, whose underlying
model changes over 2024–2026 and makes the training distribution non-stationary.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
NWP_MODELS = ["ecmwf_ifs025", "gfs_seamless", "icon_seamless"]
NWP_VARIABLES = [
    "shortwave_radiation", "direct_radiation", "diffuse_radiation", "cloud_cover",
    "precipitation", "temperature_2m", "relative_humidity_2m", "dew_point_2m", "cape", "pressure_msl",
]


def fetch_day_ahead(site: dict, model: str, start: str, end: str, cache_dir: Path, retries: int = 3) -> pd.DataFrame:
    """Hourly day-ahead (`_previous_day1`) forecast for one site and model, cached as parquet."""
    cache = cache_dir / f"{site['site_id']}_{model}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    params = {
        "latitude": site["latitude"], "longitude": site["longitude"],
        "start_date": start, "end_date": end, "timezone": "Asia/Kolkata", "models": model,
        "hourly": ",".join(f"{v}_previous_day1" for v in NWP_VARIABLES),
    }
    for attempt in range(retries):
        try:
            r = requests.get(PREVIOUS_RUNS_URL, params=params, timeout=180)
            r.raise_for_status()
            break
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    df = pd.DataFrame(r.json()["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    df = df.rename(columns={f"{v}_previous_day1": v for v in NWP_VARIABLES})
    # Drop variables this model does not provide at all (all-null) — never fill them with zeros
    df = df.dropna(axis=1, how="all")
    cache_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache, index=False)
    return df
