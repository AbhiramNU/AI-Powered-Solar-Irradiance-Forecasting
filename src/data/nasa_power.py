"""
NASA POWER API module.

Fetches hourly GHI (ALLSKY_SFC_SW_DWN), used only as an independent cross-check of ERA5.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
import requests

from src.config import NASA_POWER_URL

logger = logging.getLogger(__name__)

NASA_FILL_VALUE = -999.0


def fetch_nasa_power_ghi(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    timeout: float = 120.0,
    session: Optional[requests.Session] = None,
) -> pd.DataFrame:
    """
    Fetch hourly GHI (ALLSKY_SFC_SW_DWN) from the NASA POWER Hourly Point API.

    The API returns local solar time unless ``time-standard=UTC`` is requested, so it is
    always requested explicitly. Dates are UTC calendar days.

    Returns:
        DataFrame with a tz-aware UTC ``time`` column (the hour stamp as published by
        NASA POWER) and ``ALLSKY_SFC_SW_DWN`` (Wh/m² per hour, i.e. mean W/m²). Fill
        values (-999) become NaN.

    Raises:
        requests.HTTPError: If HTTP request fails.
        ValueError: If the response is invalid, missing the parameter, or not in UTC.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start": start_date.replace("-", ""),
        "end": end_date.replace("-", ""),
        "parameters": "ALLSKY_SFC_SW_DWN",
        "community": "RE",
        "format": "JSON",
        "time-standard": "UTC",
    }

    req_session = session or requests.Session()

    try:
        response = req_session.get(NASA_POWER_URL, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        logger.error(f"HTTP request error fetching NASA POWER data: {err}")
        raise

    try:
        payload = response.json()
    except Exception as exc:
        raise ValueError(f"Failed to parse JSON response from NASA POWER API: {exc}") from exc

    header = payload.get("header", {})
    time_standard = str(header.get("time_standard", "UTC")).upper()
    if time_standard != "UTC":
        raise ValueError(f"NASA POWER returned time standard '{time_standard}', expected UTC")

    parameters = payload.get("properties", {}).get("parameter", {})
    if "ALLSKY_SFC_SW_DWN" not in parameters:
        raise ValueError("NASA POWER API response is missing requested parameter 'ALLSKY_SFC_SW_DWN'")

    raw_series = parameters["ALLSKY_SFC_SW_DWN"]
    if not raw_series:
        raise ValueError("NASA POWER 'ALLSKY_SFC_SW_DWN' parameter series is empty")

    values = pd.to_numeric(pd.Series(list(raw_series.values())), errors="coerce").astype(float)
    values = values.mask(np.isclose(values, NASA_FILL_VALUE))
    df = pd.DataFrame({
        "time": pd.to_datetime(list(raw_series.keys()), format="%Y%m%d%H", utc=True),
        "ALLSKY_SFC_SW_DWN": values.to_numpy(),
    })

    df.attrs["header"] = header
    df.attrs["units"] = payload.get("parameters", {}).get("ALLSKY_SFC_SW_DWN", {}).get("units", "Wh/m^2")
    return df
