"""
Central configuration for the Solar Irradiance Prediction PoC.

Paths and API endpoints are constants. Everything that defines an experiment
(dates, splits, NWP models, hyperparameters, calibration targets) lives in
``config/run.json`` and is loaded with :func:`load_run_config`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# Paths
ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
SAMPLES_DATA_DIR = DATA_DIR / "samples"
REPORTS_DIR = ROOT_DIR / "reports"
RUNS_DIR = ROOT_DIR / "runs"

DASHBOARD_DIR = ROOT_DIR / "solar-irradiance-poc"
DASHBOARD_DATA_DIR = DASHBOARD_DIR / "data"
FRONTEND_DATA_DIR = DASHBOARD_DIR / "frontend" / "public" / "data"
CONTRACT_DOC = DASHBOARD_DIR / "docs" / "output_contract.md"

SITES_CONFIG_FILE = CONFIG_DIR / "sites.json"
RUN_CONFIG_FILE = CONFIG_DIR / "run.json"
DATA_AVAILABILITY_REPORT = REPORTS_DIR / "data_availability.md"
SOLAR6_RESULTS_JSON = REPORTS_DIR / "solar6_results.json"

# Timezone
DEFAULT_TIMEZONE = "Asia/Kolkata"

# SOLAR-6 spike variables (day-ahead / 1-day lead time, pinned ECMWF IFS)
REQUIRED_FORECAST_VARIABLES = [
    "shortwave_radiation_previous_day1",
    "cloud_cover_previous_day1",
    "temperature_2m_previous_day1",
    "relative_humidity_2m_previous_day1",
]

VARIABLE_NAME_MAP = {
    "shortwave_radiation_previous_day1": "Forecast GHI",
    "cloud_cover_previous_day1": "Total Cloud Cover",
    "temperature_2m_previous_day1": "Temperature",
    "relative_humidity_2m_previous_day1": "Relative Humidity",
}

# API Endpoints
OPEN_METEO_PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
OPEN_METEO_ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"


@dataclass(frozen=True)
class RunConfig:
    """Typed view of ``config/run.json``. ``raw`` keeps the full document for run records."""

    run_name: str
    start_date: str
    end_date: str
    timezone: str
    splits: Dict[str, List[int]]
    nwp_models: Dict[str, str]
    nwp_primary: str
    nwp_required_variables: List[str]
    nwp_optional_variables: List[str]
    daylight_clearsky_wm2: float
    clearsky_substeps_per_hour: int
    max_target_null_fraction: float
    max_primary_ghi_null_fraction_test: float
    quantiles: Dict[str, float]
    model_params: Dict[str, Any]
    early_stopping_rounds: int
    refit_tree_scale: float
    coverage_target_pct: float
    per_site_calibration: bool
    blend_weight_grid: List[float]
    band_multiplier_grid: List[float]
    bootstrap_samples: int
    bootstrap_seed: int
    interval_level: float
    raw: Dict[str, Any]

    def split_of_year(self, year: int) -> str:
        for name, years in self.splits.items():
            if year in years:
                return name
        return "unused"


def _grid(spec: Dict[str, float]) -> List[float]:
    return [round(float(v), 6) for v in np.linspace(spec["start"], spec["stop"], int(spec["num"]))]


def load_run_config(path: Path | str = RUN_CONFIG_FILE) -> RunConfig:
    """Load and sanity-check the run configuration."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    splits = {k: [int(y) for y in v] for k, v in raw["splits"].items()}
    for required in ("train", "validation", "test"):
        if not splits.get(required):
            raise ValueError(f"run config: split '{required}' must list at least one year")
    seen: set[int] = set()
    for years in splits.values():
        if seen & set(years):
            raise ValueError("run config: a year appears in more than one split")
        seen |= set(years)
    if max(splits["train"] + splits["validation"]) >= min(splits["test"]):
        raise ValueError("run config: test years must come after train and validation years")

    nwp = raw["nwp"]
    if nwp["primary"] not in nwp["models"]:
        raise ValueError("run config: nwp.primary must be one of nwp.models")

    return RunConfig(
        run_name=raw["run_name"],
        start_date=raw["start_date"],
        end_date=raw["end_date"],
        timezone=raw["timezone"],
        splits=splits,
        nwp_models=dict(nwp["models"]),
        nwp_primary=nwp["primary"],
        nwp_required_variables=list(nwp["required_variables"]),
        nwp_optional_variables=list(nwp["optional_variables"]),
        daylight_clearsky_wm2=float(raw["daylight_clearsky_wm2"]),
        clearsky_substeps_per_hour=int(raw["clearsky_substeps_per_hour"]),
        max_target_null_fraction=float(raw["quality"]["max_target_null_fraction"]),
        max_primary_ghi_null_fraction_test=float(raw["quality"]["max_primary_ghi_null_fraction_test"]),
        quantiles={k: float(v) for k, v in raw["model"]["quantiles"].items()},
        model_params=dict(raw["model"]["params"]),
        early_stopping_rounds=int(raw["model"]["early_stopping_rounds"]),
        refit_tree_scale=float(raw["model"]["refit_tree_scale"]),
        coverage_target_pct=float(raw["calibration"]["coverage_target_pct"]),
        per_site_calibration=bool(raw["calibration"]["per_site"]),
        blend_weight_grid=_grid(raw["calibration"]["blend_weight_grid"]),
        band_multiplier_grid=_grid(raw["calibration"]["band_multiplier_grid"]),
        bootstrap_samples=int(raw["evaluation"]["bootstrap_samples"]),
        bootstrap_seed=int(raw["evaluation"]["bootstrap_seed"]),
        interval_level=float(raw["evaluation"]["interval_level"]),
        raw=raw,
    )
