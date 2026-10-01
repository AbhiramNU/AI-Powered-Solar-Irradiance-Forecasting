"""
PyTest Suite for Saturday & Sunday Deliverables (SOLAR-12 to SOLAR-15 & Dashboard Data Loaders).

Date: 4 October 2026
Author: Akshant
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.config import (
    PROCESSED_DATA_DIR,
    REPORTS_DIR,
)

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
DASHBOARD_DATA_DIR = Path(__file__).resolve().parents[1] / "solar-irradiance-poc" / "data"


def test_model_pickle_files_exist():
    """SOLAR-12: Check that trained quantile model files exist."""
    assert (MODELS_DIR / "lightgbm_q10.pkl").exists()
    assert (MODELS_DIR / "lightgbm_q50.pkl").exists()
    assert (MODELS_DIR / "lightgbm_q90.pkl").exists()


def test_ml_model_beats_baselines():
    """SOLAR-12: Verify P50 MAE is lower than both NWP and Persistence baselines."""
    metrics_file = REPORTS_DIR / "metrics.json"
    assert metrics_file.exists()

    with open(metrics_file, "r") as f:
        metrics = json.load(f)

    overall = metrics["overall"]
    ml_mae = overall["ml_model_p50"]["mae"]
    nwp_mae = overall["raw_nwp"]["mae"]
    pers_mae = overall["persistence"]["mae"]

    assert ml_mae < nwp_mae, f"ML P50 MAE ({ml_mae}) must beat NWP MAE ({nwp_mae})"
    assert ml_mae < pers_mae, f"ML P50 MAE ({ml_mae}) must beat Persistence MAE ({pers_mae})"


def test_p10_p90_coverage_and_zero_crossings():
    """SOLAR-13: Verify P10-P90 coverage is between 75% and 85% and 0 crossings exist."""
    metrics_file = REPORTS_DIR / "metrics.json"
    with open(metrics_file, "r") as f:
        metrics = json.load(f)

    cov = metrics["overall"]["p10_p90_coverage"]
    crossings = metrics["overall"]["quantile_crossings"]

    assert 75.0 <= cov <= 85.5, f"Coverage ({cov}%) must be between 75% and 85.5%"
    assert crossings == 0, f"Quantile crossings ({crossings}) must be zero"


def test_confidence_flag_error_ordering():
    """SOLAR-14: Verify Low-confidence days have higher MAE than High-confidence days."""
    metrics_file = REPORTS_DIR / "metrics.json"
    with open(metrics_file, "r") as f:
        metrics = json.load(f)

    by_conf = metrics["by_confidence"]
    high_mae = by_conf["High"]["mae"]
    low_mae = by_conf["Low"]["mae"]

    assert low_mae > high_mae, f"Low confidence MAE ({low_mae}) should be higher than High confidence MAE ({high_mae})"


def test_final_output_contract_files():
    """SOLAR-15: Verify forecasts.parquet and metrics.json exist in dashboard data dir."""
    assert (DASHBOARD_DATA_DIR / "forecasts.parquet").exists()
    assert (DASHBOARD_DATA_DIR / "sites.json").exists()
    assert (DASHBOARD_DATA_DIR / "metrics.json").exists()

    df = pd.read_parquet(DASHBOARD_DATA_DIR / "forecasts.parquet")
    assert len(df) == 120480

    # P10 <= P50 <= P90 row check
    invalid_rows = df[(df["ghi_p10"] > df["ghi_p50"]) | (df["ghi_p50"] > df["ghi_p90"])]
    assert len(invalid_rows) == 0
