"""
Data validation for solar irradiance datasets.

``validate_api_dataframe`` inspects a raw API response and reports issues without
mutating it. ``DataQualityError`` is raised by pipeline stages when data fails a hard
quality gate; nothing downstream is allowed to paper over such failures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd


class DataQualityError(ValueError):
    """Raised when input data fails a hard quality gate."""


def validate_api_dataframe(
    df: pd.DataFrame,
    source_name: str,
    expected_columns: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    irradiance_columns: Optional[List[str]] = None,
    expected_freq: str = "h",
) -> Dict[str, Any]:
    """
    Validate an API response DataFrame.

    Checks performed:
    - Non-empty dataframe
    - Mandatory columns present
    - Timestamps monotonic, unique and on a regular grid
    - Requested date range actually covered
    - Missing values per column, and columns that are entirely null
    - Physically impossible negative values in irradiance columns

    Returns:
        Dict with ``valid``, ``issues`` and summary statistics.
    """
    results: Dict[str, Any] = {
        "source": source_name,
        "valid": True,
        "row_count": len(df),
        "columns": list(df.columns),
        "issues": [],
        "missing_values": {},
        "all_null_columns": [],
        "negative_values": {},
        "is_monotonic": True,
        "has_duplicates": False,
        "has_gaps": False,
    }
    critical: List[str] = []

    if df.empty:
        results["valid"] = False
        results["issues"].append("DataFrame is empty (0 rows).")
        return results

    missing_cols = [col for col in expected_columns if col not in df.columns]
    if missing_cols:
        critical.append(f"Missing expected columns: {missing_cols}")

    if "time" in df.columns:
        time_series = pd.to_datetime(df["time"])

        if not time_series.is_monotonic_increasing:
            results["is_monotonic"] = False
            critical.append("Timestamps are not monotonically increasing.")

        dup_count = int(time_series.duplicated().sum())
        if dup_count > 0:
            results["has_duplicates"] = True
            results["issues"].append(f"Found {dup_count} duplicate timestamp(s).")

        unique_times = time_series.drop_duplicates().sort_values()
        if len(unique_times) > 1:
            expected = pd.date_range(unique_times.iloc[0], unique_times.iloc[-1], freq=expected_freq)
            gap_count = len(expected) - len(unique_times)
            if gap_count > 0:
                results["has_gaps"] = True
                results["issues"].append(f"Found {gap_count} missing timestamp(s) on the {expected_freq} grid.")

        if start_date and end_date:
            actual_start = time_series.min().strftime("%Y-%m-%d")
            actual_end = time_series.max().strftime("%Y-%m-%d")
            results["actual_start"] = actual_start
            results["actual_end"] = actual_end
            if actual_start > start_date or actual_end < end_date:
                critical.append(
                    f"Date range {actual_start}..{actual_end} does not cover requested {start_date}..{end_date}."
                )

    for col in df.columns:
        null_cnt = int(df[col].isnull().sum())
        results["missing_values"][col] = null_cnt
        if null_cnt == len(df) and col != "time":
            results["all_null_columns"].append(col)
            critical.append(f"Column '{col}' is entirely null.")
        elif null_cnt > 0:
            results["issues"].append(f"Column '{col}' has {null_cnt} missing (null/NaN) value(s).")

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

    if critical:
        results["valid"] = False
        results["issues"] = critical + results["issues"]

    return results
