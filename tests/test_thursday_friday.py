"""
Comprehensive PyTest Suite for Thursday & Friday Sprint Deliverables (SOLAR-7 to SOLAR-11, SOLAR-18, SOLAR-19).

Date: 2 October 2026
Author: Akshant
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.config import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    REPORTS_DIR,
    SITES_CONFIG_FILE,
)


def test_sites_configuration_exists_and_valid():
    assert SITES_CONFIG_FILE.exists()
    with open(SITES_CONFIG_FILE, "r") as f:
        sites = json.load(f)
    assert len(sites) == 5
    site_ids = {s["site_id"] for s in sites}
    assert site_ids == {"JDH", "DEL", "AMD", "NAG", "CHE"}


def test_raw_data_files_exist_for_all_sites():
    """SOLAR-7 & SOLAR-8: Verify raw forecast and ERA5 datasets exist."""
    site_ids = ["JDH", "DEL", "AMD", "NAG", "CHE"]
    for sid in site_ids:
        prev_file = RAW_DATA_DIR / f"{sid}_previous_runs.parquet"
        era5_file = RAW_DATA_DIR / f"{sid}_era5.parquet"
        nasa_file = RAW_DATA_DIR / f"{sid}_nasa_power.parquet"
        assert prev_file.exists(), f"Missing {prev_file}"
        assert era5_file.exists(), f"Missing {era5_file}"
        assert nasa_file.exists(), f"Missing {nasa_file}"


def test_cleaned_data_schema_and_night_hours():
    """SOLAR-9: Check IST alignment, night hour zeroing, and no NaN values."""
    cleaned_file = PROCESSED_DATA_DIR / "cleaned_solar_data.parquet"
    assert cleaned_file.exists()
    df = pd.read_parquet(cleaned_file)
    assert len(df) == 120480  # 5 sites * 24,096 hours
    assert df.isna().sum().sum() == 0

    # Night hours check (between 21:00 and 04:00 IST GHI should be zero)
    night_df = df[df["hour_ist"].isin([22, 23, 0, 1, 2, 3])]
    assert (night_df["ghi_actual"] == 0).all()
    assert (night_df["ghi_nwp"] == 0).all()


def test_feature_table_structure_and_splits():
    """SOLAR-10: Check pvlib features and train/tune/test splits."""
    ft_file = PROCESSED_DATA_DIR / "feature_table.parquet"
    assert ft_file.exists()
    df = pd.read_parquet(ft_file)

    required_cols = [
        "site_id", "time_ist", "ghi_nwp", "ghi_actual", "solar_zenith",
        "solar_elevation", "ghi_clearsky", "kt_actual", "kt_nwp",
        "sin_doy", "cos_doy", "lag_kt_24h", "split"
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing feature column: {col}"

    splits = set(df["split"].unique())
    assert splits == {"train", "tune", "test"}
    assert len(df[df["split"] == "train"]) == 43920  # 2024
    assert len(df[df["split"] == "tune"]) == 43800   # 2025
    assert len(df[df["split"] == "test"]) == 32760   # 2026 (Jan-Sep)


def test_baselines_in_forecasts_contract():
    """SOLAR-11: Verify both baselines (NWP and Persistence) are exported."""
    forecast_file = PROCESSED_DATA_DIR / "forecasts.parquet"
    assert forecast_file.exists()
    df = pd.read_parquet(forecast_file)

    assert "ghi_nwp" in df.columns
    assert "ghi_persistence" in df.columns
    assert "ghi_actual" in df.columns
    assert "split" in df.columns


def test_metrics_json_structure():
    """SOLAR-11: Verify metrics.json output."""
    metrics_file = REPORTS_DIR / "metrics.json"
    assert metrics_file.exists()
    with open(metrics_file, "r") as f:
        metrics = json.load(f)

    assert "overall" in metrics
    assert "by_site" in metrics
    assert "raw_nwp" in metrics["overall"]
    assert "persistence" in metrics["overall"]

    # Verify NWP MAE < Persistence MAE on baseline evaluation
    nwp_mae = metrics["overall"]["raw_nwp"]["mae"]
    pers_mae = metrics["overall"]["persistence"]["mae"]
    assert nwp_mae > 0 and pers_mae > 0
