"""
SOLAR-10 — Feature Engineering & Feature Table Assembly Script.

Computes sun position, clear-sky GHI (pvlib), clear-sky index (kt),
seasonal DOY encodings, lag features, and time-based train/tune/test splits.

Date: 2 October 2026
Author: Akshant
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pvlib

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import (
    DEFAULT_TIMEZONE,
    PROCESSED_DATA_DIR,
)
from src.data.sites import load_and_validate_sites

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def compute_pvlib_features(df: pd.DataFrame, site: dict) -> pd.DataFrame:
    """Compute clear-sky irradiance and solar zenith/elevation using pvlib."""
    lat = site["latitude"]
    lon = site["longitude"]
    site_id = site["site_id"]

    location = pvlib.location.Location(latitude=lat, longitude=lon, tz=DEFAULT_TIMEZONE, name=site["name"])

    # Create localized DatetimeIndex for pvlib calculations
    times = pd.DatetimeIndex(df["time_ist"]).tz_localize(DEFAULT_TIMEZONE)

    # Solar position
    solar_pos = location.get_solarposition(times)
    solar_zenith = solar_pos["zenith"].values
    solar_elevation = solar_pos["elevation"].values

    # Clear sky GHI (Ineichen model)
    clearsky = location.get_clearsky(times, model="ineichen")
    ghi_clearsky = np.maximum(0, clearsky["ghi"].values)

    df["solar_zenith"] = solar_zenith
    df["solar_elevation"] = solar_elevation
    df["ghi_clearsky"] = ghi_clearsky

    # Clear-sky index (kt) = actual GHI / clear-sky GHI (daytime only)
    daytime_mask = (solar_elevation > 5) & (ghi_clearsky > 50)
    kt_actual = np.zeros(len(df))
    kt_actual[daytime_mask] = np.clip(df.loc[daytime_mask, "ghi_actual"] / ghi_clearsky[daytime_mask], 0.0, 1.5)
    
    kt_nwp = np.zeros(len(df))
    kt_nwp[daytime_mask] = np.clip(df.loc[daytime_mask, "ghi_nwp"] / ghi_clearsky[daytime_mask], 0.0, 1.5)

    df["kt_actual"] = kt_actual
    df["kt_nwp"] = kt_nwp

    # Day-of-year cyclical encodings
    doy = pd.to_datetime(df["time_ist"]).dt.dayofyear
    df["sin_doy"] = np.sin(2 * np.pi * doy / 365.25)
    df["cos_doy"] = np.cos(2 * np.pi * doy / 365.25)

    # Hour-of-day cyclical encodings
    hour = pd.to_datetime(df["time_ist"]).dt.hour
    df["sin_hour"] = np.sin(2 * np.pi * hour / 24.0)
    df["cos_hour"] = np.cos(2 * np.pi * hour / 24.0)

    # Lag feature: previous day's observed clear-sky index at same hour (24-hour lag)
    df["lag_kt_24h"] = df["kt_actual"].shift(24).fillna(0.0)

    # Train / Tune / Test split column
    year = pd.to_datetime(df["time_ist"]).dt.year
    split = np.where(year == 2024, "train", np.where(year == 2025, "tune", "test"))
    df["split"] = split

    return df


def main():
    print("=" * 70)
    print("SOLAR-10: FEATURE ENGINEERING & FEATURE TABLE ASSEMBLY")
    print("=" * 70)

    cleaned_data_path = PROCESSED_DATA_DIR / "cleaned_solar_data.parquet"
    if not cleaned_data_path.exists():
        raise FileNotFoundError(f"Cleaned dataset missing at {cleaned_data_path}. Run clean_data.py first.")

    df_cleaned = pd.read_parquet(cleaned_data_path)
    sites = load_and_validate_sites()
    sites_dict = {s["site_id"]: s for s in sites}

    featured_dfs = []

    for site_id, group in df_cleaned.groupby("site_id"):
        site = sites_dict[site_id]
        logger.info(f"Computing pvlib clear-sky & lag features for site {site['name']} ({site_id})...")
        group_featured = compute_pvlib_features(group.copy(), site)
        featured_dfs.append(group_featured)

    feature_table = pd.concat(featured_dfs, ignore_index=True)
    out_path = PROCESSED_DATA_DIR / "feature_table.parquet"
    feature_table.to_parquet(out_path, index=False)

    # Summary
    split_counts = feature_table["split"].value_counts().to_dict()
    print("\n" + "=" * 50)
    print("FEATURE TABLE SUMMARY")
    print("=" * 50)
    print(f"Total rows: {len(feature_table):,}")
    print(f"Total features: {len(feature_table.columns)}")
    print(f"Split breakdown: Train (2024): {split_counts.get('train', 0):,}, Tune (2025): {split_counts.get('tune', 0):,}, Test (2026): {split_counts.get('test', 0):,}")
    print(f"Saved to: {out_path}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
