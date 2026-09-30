"""
NASA POWER API module.

Fetches hourly GHI (ALLSKY_SFC_SW_DWN) solar irradiance data as an independent cross-check.
"""

from __future__ import annotations

import logging
from typing import Optional
import numpy as np
import pandas as pd
import requests

from src.config import DEFAULT_TIMEZONE, NASA_POWER_URL

logger = logging.getLogger(__name__)


def fetch_nasa_power_ghi(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    timezone: str = DEFAULT_TIMEZONE,
    timeout: float = 30.0,
    session: Optional[requests.Session] = None,
) -> pd.DataFrame:
    """
    Fetch hourly GHI (ALLSKY_SFC_SW_DWN) from NASA POWER Hourly Point API.

    Args:
        latitude: Latitude of location.
        longitude: Longitude of location.
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).
        timezone: Target timezone to convert timestamps to (default: Asia/Kolkata).
        timeout: HTTP request timeout in seconds.
        session: Optional requests.Session instance to reuse.

    Returns:
        pd.DataFrame: DataFrame containing 'time' and 'ALLSKY_SFC_SW_DWN' (or 'nasa_power_ghi').

    Raises:
        requests.HTTPError: If HTTP request fails.
        ValueError: If response is invalid or missing expected parameter data.
    """
    # NASA POWER API expects YYYYMMDD
    formatted_start = start_date.replace("-", "")
    formatted_end = end_date.replace("-", "")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start": formatted_start,
        "end": formatted_end,
        "parameters": "ALLSKY_SFC_SW_DWN",
        "community": "RE",
        "format": "JSON",
    }

    req_session = session or requests.Session()

    try:
        response = req_session.get(
            NASA_POWER_URL,
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        logger.error(f"HTTP request error fetching NASA POWER data: {err}")
        raise

    try:
        payload = response.json()
    except Exception as exc:
        raise ValueError(f"Failed to parse JSON response from NASA POWER API: {exc}") from exc

    properties = payload.get("properties", {})
    parameters = properties.get("parameter", {})

    if "ALLSKY_SFC_SW_DWN" not in parameters:
        raise ValueError("NASA POWER API response is missing requested parameter 'ALLSKY_SFC_SW_DWN'")

    raw_series = parameters["ALLSKY_SFC_SW_DWN"]
    if not raw_series:
        raise ValueError("NASA POWER 'ALLSKY_SFC_SW_DWN' parameter series is empty")

    # Timestamps in raw_series are YYYYMMDDHH in UTC
    timestamps = []
    values = []

    for ts_str, val in raw_series.items():
        # ts_str is e.g. '2026010500' -> YYYY-MM-DD HH:00:00 UTC
        dt_utc = pd.to_datetime(ts_str, format="%Y%m%d%H", utc=True)
        timestamps.append(dt_utc)
        # Replace missing value fill value -999.0 with NaN
        clean_val = np.nan if val in (-999.0, -999, "-999", "-999.0") else float(val)
        values.append(clean_val)

    df = pd.DataFrame({
        "time": timestamps,
        "ALLSKY_SFC_SW_DWN": values,
    })

    # Convert to local timezone (Asia/Kolkata) and format time
    if timezone:
        df["time"] = df["time"].dt.tz_convert(timezone)

    # Convert tz-aware datetime to string or localized datetime without tz for easy alignment
    df["time"] = df["time"].dt.strftime("%Y-%m-%dT%H:%M")
    df["time"] = pd.to_datetime(df["time"])

    # Metadata attached to dataframe attrs
    df.attrs["header"] = payload.get("header", {})
    df.attrs["units"] = payload.get("parameters", {}).get("ALLSKY_SFC_SW_DWN", {}).get("units", "Wh/m^2")

    return df
