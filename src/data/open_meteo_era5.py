"""
Open-Meteo ERA5 Historical Weather API module.

Fetches historical ground truth Global Horizontal Irradiance (GHI) / shortwave radiation data.
"""

from __future__ import annotations

import logging
from typing import Optional
import pandas as pd
import requests

from src.config import DEFAULT_TIMEZONE, OPEN_METEO_ERA5_URL

logger = logging.getLogger(__name__)


def fetch_era5_ghi(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    timezone: str = DEFAULT_TIMEZONE,
    timeout: float = 30.0,
    session: Optional[requests.Session] = None,
) -> pd.DataFrame:
    """
    Fetch hourly GHI / shortwave radiation ground truth from Open-Meteo ERA5 Archive API.

    Args:
        latitude: Latitude of location.
        longitude: Longitude of location.
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).
        timezone: Target timezone string (default: Asia/Kolkata).
        timeout: HTTP request timeout in seconds.
        session: Optional requests.Session instance to reuse.

    Returns:
        pd.DataFrame: DataFrame containing 'time' and 'shortwave_radiation' columns.

    Raises:
        requests.HTTPError: If HTTP request fails.
        ValueError: If response is invalid or missing required variables.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "shortwave_radiation",
        "timezone": timezone,
    }

    req_session = session or requests.Session()

    try:
        response = req_session.get(
            OPEN_METEO_ERA5_URL,
            params=params,
            timeout=timeout,
        )
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

    df["time"] = pd.to_datetime(df["time"])

    return df
