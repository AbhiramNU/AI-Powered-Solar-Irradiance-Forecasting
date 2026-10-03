"""
Open-Meteo Previous Runs API module.

Fetches day-ahead (``_previous_day1``) forecast variables for one pinned NWP model.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Sequence

import pandas as pd
import requests

from src.config import (
    DEFAULT_TIMEZONE,
    OPEN_METEO_PREVIOUS_RUNS_URL,
    REQUIRED_FORECAST_VARIABLES,
)
from src.data.validation import DataQualityError

logger = logging.getLogger(__name__)


def fetch_previous_run(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    variables: Optional[List[str]] = None,
    model: Optional[str] = None,
    required: Optional[Sequence[str]] = None,
    timezone: str = DEFAULT_TIMEZONE,
    timeout: float = 180.0,
    session: Optional[requests.Session] = None,
) -> pd.DataFrame:
    """
    Fetch day-ahead variables from the Open-Meteo Previous Runs API.

    Args:
        latitude, longitude: Site coordinates.
        start_date, end_date: Inclusive date range (YYYY-MM-DD), in ``timezone``.
        variables: Hourly variable names to request (defaults to REQUIRED_FORECAST_VARIABLES).
        model: Open-Meteo model id (e.g. ``ecmwf_ifs025``). ``None`` uses ``best_match``,
            whose underlying model changes over time; pin a model for training data.
        required: Variables that must contain data. Defaults to all requested variables.
            An all-null required variable raises; an all-null optional variable is dropped
            and listed in ``df.attrs["dropped_all_null"]``.
        timezone: Timezone the API should use for the hourly grid.
        timeout: HTTP request timeout in seconds.
        session: Optional requests.Session to reuse.

    Returns:
        DataFrame with a tz-aware ``time`` column (interval end, hourly) and the variables.

    Raises:
        requests.HTTPError: If the HTTP request fails.
        ValueError: If the response is malformed or a requested variable is absent.
        DataQualityError: If a required variable is entirely null.
    """
    if variables is None:
        variables = REQUIRED_FORECAST_VARIABLES
    required = list(variables if required is None else required)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(variables),
        "timezone": timezone,
    }
    if model:
        params["models"] = model

    req_session = session or requests.Session()

    try:
        response = req_session.get(OPEN_METEO_PREVIOUS_RUNS_URL, params=params, timeout=timeout)
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

    missing_vars = [var for var in variables if var not in hourly_data]
    if missing_vars:
        raise ValueError(f"Previous Runs API response is missing requested variable(s): {missing_vars}")

    df = pd.DataFrame(hourly_data)
    if df.empty:
        raise ValueError("Parsed DataFrame from Previous Runs API is empty")

    all_null = [var for var in variables if df[var].isna().all()]
    required_null = [var for var in all_null if var in required]
    if required_null:
        raise DataQualityError(
            f"Previous Runs API returned no data for required variable(s) {required_null} "
            f"(model={model or 'best_match'})"
        )
    if all_null:
        logger.warning(f"Dropping all-null optional variable(s) {all_null} (model={model or 'best_match'})")
        df = df.drop(columns=all_null)

    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(timezone)
    df.attrs["dropped_all_null"] = all_null
    df.attrs["model"] = model or "best_match"
    return df
