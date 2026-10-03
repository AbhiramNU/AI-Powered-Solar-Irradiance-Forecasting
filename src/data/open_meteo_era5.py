"""
Open-Meteo ERA5 Historical Weather API module.

Fetches ERA5 hourly GHI (``shortwave_radiation``), the PoC's reference "actual".
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import requests

from src.config import DEFAULT_TIMEZONE, OPEN_METEO_ERA5_URL
from src.data.validation import DataQualityError

logger = logging.getLogger(__name__)


def fetch_era5_ghi(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    timezone: str = DEFAULT_TIMEZONE,
    model: str = "era5",
    timeout: float = 120.0,
    session: Optional[requests.Session] = None,
) -> pd.DataFrame:
    """
    Fetch hourly GHI from the Open-Meteo archive API.

    The archive's default ``best_match`` blends several reanalyses and analyses, so the
    model is pinned (``era5`` by default) to keep the target consistent over time.
    Values are means over the hour ending at ``time``.

    Returns:
        DataFrame with a tz-aware ``time`` column and ``shortwave_radiation`` (W/m²).

    Raises:
        requests.HTTPError: If HTTP request fails.
        ValueError: If response is invalid or missing required variables.
        DataQualityError: If the GHI series is entirely null.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "shortwave_radiation",
        "timezone": timezone,
        "models": model,
    }

    req_session = session or requests.Session()

    try:
        response = req_session.get(OPEN_METEO_ERA5_URL, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        logger.error(f"HTTP request error fetching ERA5 data: {err}")
        raise

    try:
        payload = response.json()
    except Exception as exc:
        raise ValueError(f"Failed to parse JSON response from ERA5 API: {exc}") from exc

    if "hourly" not in payload:
        raise ValueError("ERA5 API response does not contain 'hourly' data block")

    hourly_data = payload["hourly"]
    if not isinstance(hourly_data, dict) or "time" not in hourly_data:
        raise ValueError("ERA5 API response 'hourly' block is missing 'time' field")

    if "shortwave_radiation" not in hourly_data:
        raise ValueError("ERA5 API response is missing requested variable 'shortwave_radiation'")

    df = pd.DataFrame(hourly_data)

    if df.empty:
        raise ValueError("Parsed DataFrame from ERA5 API is empty")
    if df["shortwave_radiation"].isna().all():
        raise DataQualityError("ERA5 API returned no GHI data for the requested period")

    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(timezone)
    return df
