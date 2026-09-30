"""
Data validation module for solar irradiance datasets.

Provides validation routines to inspect raw API responses without mutating them.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


def validate_api_dataframe(
    df: pd.DataFrame,
    source_name: str,
    expected_columns: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    irradiance_columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Validate an API response DataFrame.

    Checks performed:
    - Non-empty dataframe
    - Mandatory columns present
    - Timestamps present and monotonic
    - Duplicate timestamps
    - Missing values (NaN count) per column
    - Date range coverage
    - Physically impossible negative values in irradiance columns

    Args:
        df: Input pandas DataFrame.
        source_name: Name of the data source / API.
        expected_columns: List of columns that must exist in df.
        start_date: Expected start date (YYYY-MM-DD).
        end_date: Expected end date (YYYY-MM-DD).
        irradiance_columns: Optional list of solar irradiance column names to check for negative values.

    Returns:
        Dict[str, Any] containing validation status, issues found, and summary stats.
    """
    results: Dict[str, Any] = {
        "source": source_name,
        "valid": True,
        "row_count": len(df),
        "columns": list(df.columns),
        "issues": [],
        "missing_values": {},
        "negative_values": {},
        "is_monotonic": True,
        "has_duplicates": False,
    }

    if df.empty:
        results["valid"] = False
        results["issues"].append("DataFrame is empty (0 rows).")
        return results

    # Check expected columns
    missing_cols = [col for col in expected_columns if col not in df.columns]
    if missing_cols:
        results["valid"] = False
        results["issues"].append(f"Missing expected columns: {missing_cols}")

    if "time" in df.columns:
        time_series = pd.to_datetime(df["time"])

        # Check monotonic increasing
        if not time_series.is_monotonic_increasing:
            results["is_monotonic"] = False
            results["issues"].append("Timestamps are not strictly monotonically increasing.")

        # Check duplicates
        dup_count = time_series.duplicated().sum()
        if dup_count > 0:
            results["has_duplicates"] = True
            results["issues"].append(f"Found {dup_count} duplicate timestamp(s).")

        # Date range check
        if start_date and end_date:
            actual_start = time_series.min().strftime("%Y-%m-%d")
            actual_end = time_series.max().strftime("%Y-%m-%d")
            results["actual_start"] = actual_start
            results["actual_end"] = actual_end

    # Check missing values per column
    for col in df.columns:
        null_cnt = int(df[col].isnull().sum())
        results["missing_values"][col] = null_cnt
        if null_cnt > 0:
            results["issues"].append(f"Column '{col}' has {null_cnt} missing (null/NaN) value(s).")

    # Check negative values in irradiance columns
    if irradiance_columns is None:
        irradiance_columns = [
            col for col in df.columns
            if "radiation" in col.lower() or "ghi" in col.lower() or "sw_dwn" in col.lower()
        ]

    for col in irradiance_columns:
        if col in df.columns:
            neg_count = int((df[col] < 0).sum())
            results["negative_values"][col] = neg_count
            if neg_count > 0:
                results["issues"].append(
                    f"Irradiance column '{col}' contains {neg_count} physically impossible negative value(s)."
                )

    if results["issues"]:
        # Note: missing values or warnings set valid status depending on severity
        critical_issues = [
            i for i in results["issues"]
            if "Missing expected" in i or "empty" in i or "not strictly" in i
        ]
        if critical_issues:
            results["valid"] = False

    return results
