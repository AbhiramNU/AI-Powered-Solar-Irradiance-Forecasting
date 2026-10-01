"""
SOLAR-11 — Baseline Models Evaluation & Export Script.

Evaluates Baseline A (Persistence) and Baseline B (Raw NWP Forecast)
on 2025 (tune) and 2026 (test) datasets. Exports forecasts.parquet
and metrics.json conforming to the Akshant-Abhiram data contract.

Date: 2 October 2026
Author: Akshant
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import (
    PROCESSED_DATA_DIR,
    REPORTS_DIR,
)
from src.data.sites import load_and_validate_sites

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def calculate_metrics(actual: np.ndarray, pred: np.ndarray, baseline_pred: np.ndarray = None) -> Dict[str, float]:
    """Calculate MAE, RMSE, nRMSE, Bias, and Skill Score."""
    errors = pred - actual
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    mean_actual = float(np.mean(actual)) if np.mean(actual) > 0 else 1.0
    nrmse = float((rmse / mean_actual) * 100)
    bias = float(np.mean(errors))

    skill = 0.0
    if baseline_pred is not None:
        base_mae = float(np.mean(np.abs(baseline_pred - actual)))
        if base_mae > 0:
            skill = float((1.0 - (mae / base_mae)) * 100)

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "nrmse": round(nrmse, 2),
        "bias": round(bias, 2),
        "skill": round(skill, 2),
    }


def main():
    print("=" * 70)
    print("SOLAR-11: BASELINE MODELS EVALUATION & EXPORT")
    print("=" * 70)

    feature_table_path = PROCESSED_DATA_DIR / "feature_table.parquet"
    if not feature_table_path.exists():
        raise FileNotFoundError(f"Feature table missing at {feature_table_path}. Run build_feature_table.py first.")

    df = pd.read_parquet(feature_table_path)
    sites = load_and_validate_sites()

    # 1. Calculate Baseline A (Persistence GHI)
    # ghi_persistence = lag_kt_24h * ghi_clearsky
    df["ghi_persistence"] = np.clip(df["lag_kt_24h"] * df["ghi_clearsky"], 0, None)
    df.loc[df["solar_elevation"] <= 0, "ghi_persistence"] = 0.0

    # For baseline export before ML model (F1), set P50=ghi_nwp, P10=0.85*nwp, P90=1.15*nwp
    df["ghi_p50"] = df["ghi_nwp"]
    df["ghi_p10"] = np.clip(df["ghi_nwp"] * 0.85, 0, None)
    df["ghi_p90"] = np.clip(df["ghi_nwp"] * 1.15, 0, None)
    df["confidence"] = "Medium"

    # Export forecasts.parquet to processed and dashboard directories
    forecast_cols = [
        "site_id", "date", "hour_ist", "ghi_actual", "ghi_p10", "ghi_p50", "ghi_p90",
        "ghi_nwp", "ghi_persistence", "ghi_clearsky", "confidence", "split"
    ]
    forecast_df = df[forecast_cols].copy()

    out_forecast_path = PROCESSED_DATA_DIR / "forecasts.parquet"
    forecast_df.to_parquet(out_forecast_path, index=False)

    dashboard_data_dir = ROOT_DIR / "solar-irradiance-poc" / "data"
    dashboard_data_dir.mkdir(parents=True, exist_ok=True)
    forecast_df.to_parquet(dashboard_data_dir / "forecasts.parquet", index=False)

    # Copy sites.json to dashboard data dir
    sites_json_source = ROOT_DIR / "config" / "sites.json"
    with open(sites_json_source, "r") as f:
        sites_data = json.load(f)
    with open(dashboard_data_dir / "sites.json", "w") as f:
        json.dump(sites_data, f, indent=2)

    # 2. Score baselines on 2025 (tune) and 2026 (test)
    test_df = df[df["split"] == "test"].copy()
    tune_df = df[df["split"] == "tune"].copy()

    metrics_output: Dict[str, Any] = {
        "overall": {},
        "by_site": {},
        "by_month": {},
    }

    # Overall test metrics
    actual_test = test_df["ghi_actual"].values
    nwp_test = test_df["ghi_nwp"].values
    pers_test = test_df["ghi_persistence"].values

    nwp_metrics = calculate_metrics(actual_test, nwp_test, pers_test)
    pers_metrics = calculate_metrics(actual_test, pers_test)

    metrics_output["overall"] = {
        "raw_nwp": nwp_metrics,
        "persistence": pers_metrics,
    }

    # Per-site metrics
    for site in sites:
        s_id = site["site_id"]
        s_test = test_df[test_df["site_id"] == s_id]
        if len(s_test) > 0:
            act = s_test["ghi_actual"].values
            nwp_val = s_test["ghi_nwp"].values
            pers_val = s_test["ghi_persistence"].values

            metrics_output["by_site"][s_id] = {
                "name": site["name"],
                "raw_nwp": calculate_metrics(act, nwp_val, pers_val),
                "persistence": calculate_metrics(act, pers_val),
            }

    # Save metrics.json
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_metrics_path = REPORTS_DIR / "metrics.json"
    with open(out_metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_output, f, indent=2)
    with open(dashboard_data_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_output, f, indent=2)

    print("\n" + "=" * 50)
    print("BASELINE EVALUATION RESULTS (2026 TEST PERIOD)")
    print("=" * 50)
    print(f"Raw NWP Forecast MAE: {nwp_metrics['mae']} W/m² | RMSE: {nwp_metrics['rmse']} W/m²")
    print(f"Persistence Model MAE: {pers_metrics['mae']} W/m² | RMSE: {pers_metrics['rmse']} W/m²")
    print(f"\nSaved forecasts contract to: {out_forecast_path}")
    print(f"Saved metrics summary to: {out_metrics_path}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
