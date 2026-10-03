"""
Output contract between the pipeline and the dashboards.

The schemas here are the single source of truth. ``publish`` validates every file
against them before writing, and ``render_contract_markdown`` generates
``solar-irradiance-poc/docs/output_contract.md`` (a test keeps that file in sync).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

CONTRACT_VERSION = 2

SPLITS = ("train", "validation", "test")
CONFIDENCE_LEVELS = ("High", "Medium", "Low")
MODEL_KEYS = ("ml_model_p50", "raw_nwp", "persistence")
POINT_METRIC_KEYS = ("mae", "rmse", "nrmse", "bias", "skill")


class ContractError(ValueError):
    """Raised when an output does not satisfy the contract."""


@dataclass(frozen=True)
class Column:
    name: str
    kind: str  # "str" | "int" | "float" | "bool"
    description: str
    unit: str = ""
    nullable: bool = False
    min: Optional[float] = None
    max: Optional[float] = None
    allowed: Optional[Sequence[str]] = None


SITES_FIELDS: List[Column] = [
    Column("site_id", "str", "Unique site identifier"),
    Column("name", "str", "Human-readable name"),
    Column("latitude", "float", "Latitude", "degrees", min=-90, max=90),
    Column("longitude", "float", "Longitude", "degrees", min=-180, max=180),
    Column("altitude_m", "float", "Site altitude used for clear-sky", "m", min=-500, max=9000),
    Column("climate_zone", "str", "Climate zone description"),
]

FORECAST_COLUMNS: List[Column] = [
    Column("site_id", "str", "Matches `site_id` in sites.json"),
    Column("date", "str", "IST date of the interval midpoint, YYYY-MM-DD"),
    Column("hour_ist", "int", "IST hour at the middle of the one-hour averaging interval: 12 means 11:30–12:30 IST", "h", min=0, max=23),
    Column("is_daylight", "bool", "True when interval-mean clear-sky GHI exceeds the daylight threshold; metrics use these rows"),
    Column("ghi_actual", "float", "ERA5 GHI, interval mean (the reference 'actual')", "W/m²", nullable=True, min=0, max=1500),
    Column("ghi_p10", "float", "10th percentile forecast", "W/m²", min=0, max=1500),
    Column("ghi_p50", "float", "Median forecast", "W/m²", min=0, max=1500),
    Column("ghi_p90", "float", "90th percentile forecast", "W/m²", min=0, max=1500),
    Column("ghi_nwp", "float", "Raw day-ahead GHI from the primary NWP model (ECMWF IFS)", "W/m²", nullable=True, min=0, max=1500),
    Column("ghi_persistence", "float", "Idealised persistence: yesterday's clear-sky index × today's clear-sky GHI. Uses observations not available at issue time, so it is an optimistic reference", "W/m²", nullable=True, min=0, max=1500),
    Column("ghi_clearsky", "float", "Ineichen clear-sky GHI, interval mean", "W/m²", min=0, max=1500),
    Column("confidence", "str", "Day-level forecast confidence", allowed=CONFIDENCE_LEVELS),
    Column("split", "str", "Data split; only `test` rows are out-of-sample for the final model", allowed=SPLITS),
]

DAILY_COLUMNS: List[Column] = [
    Column("site_id", "str", "Matches `site_id` in sites.json"),
    Column("date", "str", "Local date (IST), YYYY-MM-DD"),
    Column("split", "str", "Data split", allowed=SPLITS),
    Column("confidence", "str", "Day-level forecast confidence", allowed=CONFIDENCE_LEVELS),
    Column("actual_kwh_m2", "float", "Daily ERA5 irradiation (NaN if any daylight hour is missing)", "kWh/m²", nullable=True, min=0, max=15),
    Column("p10_kwh_m2", "float", "Calibrated daily 10th percentile (not the sum of hourly P10s)", "kWh/m²", min=0, max=15),
    Column("p50_kwh_m2", "float", "Daily median forecast (sum of hourly P50)", "kWh/m²", min=0, max=15),
    Column("p90_kwh_m2", "float", "Calibrated daily 90th percentile (not the sum of hourly P90s)", "kWh/m²", min=0, max=15),
    Column("nwp_kwh_m2", "float", "Daily raw NWP irradiation", "kWh/m²", nullable=True, min=0, max=15),
    Column("persistence_kwh_m2", "float", "Daily idealised persistence irradiation", "kWh/m²", nullable=True, min=0, max=15),
    Column("clearsky_kwh_m2", "float", "Daily clear-sky irradiation", "kWh/m²", min=0, max=15),
]


def _check_kind(series: pd.Series, col: Column) -> bool:
    values = series.dropna()
    if col.kind == "str":
        return all(isinstance(v, str) for v in values)
    if col.kind == "int":
        return pd.api.types.is_integer_dtype(series)
    if col.kind == "float":
        return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)
    if col.kind == "bool":
        return pd.api.types.is_bool_dtype(series)
    raise ValueError(f"unknown column kind {col.kind}")


def validate_frame(df: pd.DataFrame, columns: List[Column], name: str) -> None:
    """Check presence, type, nullability, ranges and allowed values. Raises ContractError."""
    problems: List[str] = []
    for col in columns:
        if col.name not in df.columns:
            problems.append(f"missing column '{col.name}'")
            continue
        s = df[col.name]
        if not _check_kind(s, col):
            problems.append(f"column '{col.name}' is {s.dtype}, expected {col.kind}")
            continue
        n_null = int(s.isna().sum())
        if n_null and not col.nullable:
            problems.append(f"column '{col.name}' has {n_null} null value(s)")
        if col.min is not None and (s < col.min).any():
            problems.append(f"column '{col.name}' has values below {col.min}")
        if col.max is not None and (s > col.max).any():
            problems.append(f"column '{col.name}' has values above {col.max}")
        if col.allowed is not None:
            bad = sorted(set(s.dropna()) - set(col.allowed))
            if bad:
                problems.append(f"column '{col.name}' has unexpected values {bad[:5]}")
    if problems:
        raise ContractError(f"{name}: " + "; ".join(problems))


def validate_forecasts(df: pd.DataFrame) -> None:
    validate_frame(df, FORECAST_COLUMNS, "forecasts.parquet")
    if df.duplicated(["site_id", "date", "hour_ist"]).any():
        raise ContractError("forecasts.parquet: duplicate (site_id, date, hour_ist) rows")
    if ((df.ghi_p10 > df.ghi_p50) | (df.ghi_p50 > df.ghi_p90)).any():
        raise ContractError("forecasts.parquet: P10 <= P50 <= P90 violated")
    night = ~df.is_daylight
    if (df.loc[night, ["ghi_p10", "ghi_p50", "ghi_p90"]].to_numpy() != 0).any():
        raise ContractError("forecasts.parquet: non-zero forecast outside daylight")


def validate_daily(df: pd.DataFrame) -> None:
    validate_frame(df, DAILY_COLUMNS, "daily_forecasts.parquet")
    if df.duplicated(["site_id", "date"]).any():
        raise ContractError("daily_forecasts.parquet: duplicate (site_id, date) rows")
    if ((df.p10_kwh_m2 > df.p50_kwh_m2) | (df.p50_kwh_m2 > df.p90_kwh_m2)).any():
        raise ContractError("daily_forecasts.parquet: P10 <= P50 <= P90 violated")


def validate_sites(sites: Any) -> None:
    if not isinstance(sites, list) or not sites:
        raise ContractError("sites.json: must be a non-empty JSON array")
    validate_frame(pd.DataFrame(sites), SITES_FIELDS, "sites.json")


def _require(d: Dict[str, Any], keys: Sequence[str], where: str) -> None:
    missing = [k for k in keys if k not in d]
    if missing:
        raise ContractError(f"metrics.json: {where} missing {missing}")


def validate_metrics(m: Dict[str, Any], site_ids: Sequence[str]) -> None:
    _require(m, ["contract_version", "model_version", "run_id", "convention", "overall", "all_hours",
                 "daily", "by_site", "by_month", "by_confidence"], "top level")
    if m["contract_version"] != CONTRACT_VERSION:
        raise ContractError(f"metrics.json: contract_version {m['contract_version']} != {CONTRACT_VERSION}")
    for block in ("overall", "all_hours"):
        _require(m[block], list(MODEL_KEYS) + ["p10_p90_coverage"], block)
        for k in MODEL_KEYS:
            _require(m[block][k], POINT_METRIC_KEYS, f"{block}.{k}")
    _require(m["overall"], ["skill_interval", "pinball", "quantile_crossings"], "overall")
    _require(m["daily"], ["ml_model_p50", "p10_p90_coverage"], "daily")
    _require(m["by_site"], list(site_ids), "by_site")
    for sid in site_ids:
        _require(m["by_site"][sid], list(MODEL_KEYS) + ["name", "climate_zone", "coverage", "skill_interval"], f"by_site.{sid}")
    for month, block in m["by_month"].items():
        _require(block, ["overall", "by_site"], f"by_month.{month}")
    for level, block in m["by_confidence"].items():
        if level not in CONFIDENCE_LEVELS:
            raise ContractError(f"metrics.json: unknown confidence level {level}")
        _require(block, ["site_days", "mae", "coverage"], f"by_confidence.{level}")
    ind = m.get("independent_check")
    if ind is not None:
        _require(ind, ["reference", "rows", "ml_model_p50", "raw_nwp", "era5"], "independent_check")
    for v in _walk_numbers(m):
        if not np.isfinite(v):
            raise ContractError("metrics.json: contains NaN or infinite values")


def _walk_numbers(x: Any):
    if isinstance(x, dict):
        for v in x.values():
            yield from _walk_numbers(v)
    elif isinstance(x, list):
        for v in x:
            yield from _walk_numbers(v)
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        yield float(x)


def _table(columns: List[Column]) -> List[str]:
    lines = ["| Column | Type | Unit | Nullable | Allowed / range | Description |", "|---|---|---|---|---|---|"]
    for c in columns:
        rng = ", ".join(c.allowed) if c.allowed else (
            f"{'' if c.min is None else c.min}–{'' if c.max is None else c.max}" if (c.min is not None or c.max is not None) else "")
        lines.append(f"| `{c.name}` | {c.kind} | {c.unit} | {'yes' if c.nullable else 'no'} | {rng} | {c.description} |")
    return lines


def render_contract_markdown() -> str:
    """Generate the contract document from the schemas above."""
    lines = [
        "# Output Contract",
        "",
        "<!-- Generated by `python -m src.pipeline contract-doc` from src/contract.py. Do not edit by hand. -->",
        "",
        f"Contract version: **{CONTRACT_VERSION}**",
        "",
        "The pipeline (`python -m src.pipeline publish`) writes four files to `solar-irradiance-poc/data/` and",
        "validates each against this contract before writing. The React exporter derives static JSON from them.",
        "",
        "Time convention: every hourly value is a one-hour mean centred on `hour_ist` (IST). Source data are hourly",
        "means on the UTC grid, so in IST (UTC+5:30) each interval runs from (hh−1):30 to hh:30 around the labelled hour, e.g. 11:30–12:30 for hour 12.",
        "Metrics headline **daylight hours only**; all-hours figures are reported separately because night hours",
        "are trivially correct for every model and halve the apparent error.",
        "",
        "## 1. sites.json",
        "",
        "A JSON array of site objects.",
        "",
        *_table(SITES_FIELDS),
        "",
        "## 2. forecasts.parquet",
        "",
        "One row per site and hour, all hours of the configured period. Row rules: P10 ≤ P50 ≤ P90;",
        "forecasts are 0 when `is_daylight` is false; `(site_id, date, hour_ist)` is unique.",
        "",
        *_table(FORECAST_COLUMNS),
        "",
        "## 3. daily_forecasts.parquet",
        "",
        "One row per site and day. Daily P10/P90 are calibrated on the validation year for the coverage target;",
        "summing hourly quantiles would overstate the daily range.",
        "",
        *_table(DAILY_COLUMNS),
        "",
        "## 4. metrics.json",
        "",
        "All figures are computed on the test split. Point-metric blocks contain `mae`, `rmse`, `nrmse` (% of mean",
        "actual), `bias` (forecast − actual) and `skill` (% MAE reduction: ML vs raw NWP, raw NWP vs persistence).",
        "",
        "| Key | Content |",
        "|---|---|",
        f"| `contract_version` | `{CONTRACT_VERSION}` |",
        "| `model_version`, `run_id`, `generated_at`, `test_period` | Provenance |",
        "| `convention` | Plain-language description of the metric convention |",
        "| `overall` | Daylight-hour point metrics for `ml_model_p50`, `raw_nwp`, `persistence`; `p10_p90_coverage` (% of daylight hours); `skill_interval` (bootstrap interval on skill, resampling days); `pinball` per quantile; `quantile_crossings` |",
        "| `all_hours` | The same point metrics and coverage over all hours, for comparison with earlier reports |",
        "| `daily` | Daily-irradiation metrics (kWh/m²) and daily P10–P90 coverage |",
        "| `by_site.<site_id>` | `name`, `climate_zone`, daylight point metrics per model, `coverage`, `skill_interval` |",
        "| `by_month.<YYYY-MM>` | `overall` and `by_site` daylight MAE per model |",
        "| `by_confidence.<High/Medium/Low>` | `site_days`, daylight `mae`, `coverage` |",
        "| `independent_check` | Scores against NASA POWER (not used in training): `reference`, `rows`, point metrics for `ml_model_p50` (skill vs raw NWP), `raw_nwp`, `era5`; `null` if unavailable |",
        "",
    ]
    return "\n".join(lines)
