"""
Open-Meteo Previous Runs API module.

Fetches 1-day lead-time (previous runs) forecast weather variables
for solar irradiance prediction.
"""

from __future__ import annotations

import logging
from typing import List, Optional
import pandas as pd
import requests

from src.config import (
    DEFAULT_TIMEZONE,
    OPEN_METEO_PREVIOUS_RUNS_URL,
    REQUIRED_FORECAST_VARIABLES,
)

logger = logging.getLogger(__name__)


def fetch_previous_run(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    variables: Optional[List[str]] = None,
    timezone: str = DEFAULT_TIMEZONE,
    timeout: float = 30.0,
    session: Optional[requests.Session] = None,
) -> pd.DataFrame:
    """
    Fetch 1-day lead-time (previous-day forecast) variables from Open-Meteo Previous Runs API.

    Args:
        latitude: Latitude of location.
        longitude: Longitude of location.
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).
        variables: List of hourly variable names to request (defaults to REQUIRED_FORECAST_VARIABLES).
        timezone: Target timezone string (default: Asia/Kolkata).
        timeout: HTTP request timeout in seconds.
        session: Optional requests.Session instance to reuse.

    Returns:
        pd.DataFrame: Hourly dataframe containing 'time' and forecast variables.

    Raises:
        requests.HTTPError: If HTTP request fails.
        ValueError: If response is invalid, missing hourly block, or missing requested variables.
    """
    if variables is None:
        variables = REQUIRED_FORECAST_VARIABLES

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(variables),
        "timezone": timezone,
    }

    req_session = session or requests.Session()

    try:
        response = req_session.get(
            OPEN_METEO_PREVIOUS_RUNS_URL,
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        logger.error(f"HTTP request error fetching Previous Runs data: {err}")
        raise

    try:
        payload = response.json()
    except Exception as exc:
        raise ValueError(f"Failed to parse JSON response from Previous Runs API: {exc}") from exc

    if "hourly" not in payload:
        raise ValueError("API response does not contain 'hourly' data block")

    hourly_data = payload["hourly"]
    if not isinstance(hourly_data, dict) or "time" not in hourly_data:
        raise ValueError("API response 'hourly' block is missing mandatory 'time' field")

    # Check for missing requested variables in API response
    missing_vars = [var for var in variables if var not in hourly_data]
    if missing_vars:
        raise ValueError(
            f"Previous Runs API response is missing requested variable(s): {missing_vars}"
        )

    df = pd.DataFrame(hourly_data)

    if df.empty:
        raise ValueError("Parsed DataFrame from Previous Runs API is empty")

    # Convert time column to datetime
    df["time"] = pd.to_datetime(df["time"])

    return df