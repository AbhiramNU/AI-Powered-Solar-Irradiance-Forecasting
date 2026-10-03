"""
Loads the published output contract (see docs/output_contract.md).

There is deliberately no fallback to sample data: if the pipeline has not published,
pages show an error instead of numbers that did not come from the model.
"""

import json
import os

import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONTRACT_VERSION = 2

FORECAST_COLUMNS = ["site_id", "date", "hour_ist", "is_daylight", "ghi_actual", "ghi_p10", "ghi_p50", "ghi_p90",
                    "ghi_nwp", "ghi_persistence", "ghi_clearsky", "confidence", "split"]
DAILY_COLUMNS = ["site_id", "date", "split", "confidence", "actual_kwh_m2", "p10_kwh_m2", "p50_kwh_m2", "p90_kwh_m2",
                 "nwp_kwh_m2", "persistence_kwh_m2", "clearsky_kwh_m2"]
NOT_PUBLISHED = "Forecast data has not been published. Run `python -m src.pipeline publish` from the repository root."


def _path(name):
    return os.path.join(DATA_DIR, name)


@st.cache_data
def load_sites():
    try:
        with open(_path("sites.json"), "r") as f:
            sites = json.load(f)
    except FileNotFoundError:
        st.error(NOT_PUBLISHED)
        return []
    if not isinstance(sites, list) or not all(
        all(k in s for k in ("site_id", "name", "latitude", "longitude", "climate_zone")) for s in sites
    ):
        st.error("sites.json does not match the output contract.")
        return []
    return sites


def _load_parquet(name, columns):
    try:
        df = pd.read_parquet(_path(name))
    except FileNotFoundError:
        st.error(NOT_PUBLISHED)
        return pd.DataFrame()
    missing = [c for c in columns if c not in df.columns]
    if missing:
        st.error(f"{name} is missing contract columns: {missing}")
        return pd.DataFrame()
    return df


@st.cache_data
def load_forecasts():
    df = _load_parquet("forecasts.parquet", FORECAST_COLUMNS)
    if not df.empty and ((df["ghi_p10"] > df["ghi_p50"]) | (df["ghi_p50"] > df["ghi_p90"])).any():
        st.error("forecasts.parquet violates P10 ≤ P50 ≤ P90.")
        return pd.DataFrame()
    return df


@st.cache_data
def load_daily():
    return _load_parquet("daily_forecasts.parquet", DAILY_COLUMNS)


@st.cache_data
def load_metrics():
    try:
        with open(_path("metrics.json"), "r") as f:
            metrics = json.load(f)
    except FileNotFoundError:
        st.error(NOT_PUBLISHED)
        return {}
    if metrics.get("contract_version") != CONTRACT_VERSION:
        st.error(f"metrics.json contract version {metrics.get('contract_version')} is not supported (expected {CONTRACT_VERSION}).")
        return {}
    return metrics


def signed(v, digits=1):
    return f"{v:+.{digits}f}"
