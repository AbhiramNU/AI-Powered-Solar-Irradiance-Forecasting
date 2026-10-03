"""
Publish a run to the dashboards.

Copies a run's contract files into ``solar-irradiance-poc/data/`` (read by Streamlit) after
validating them, then derives the static JSON for the React frontend. There is no fallback
to sample data: if a required file is missing or invalid, publishing fails.
"""

from __future__ import annotations

import json
import logging
import math
import shutil
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.config import DASHBOARD_DATA_DIR, FRONTEND_DATA_DIR, REPORTS_DIR
from src.contract import validate_daily, validate_forecasts, validate_metrics, validate_sites

logger = logging.getLogger(__name__)

CONTRACT_FILES = ("sites.json", "forecasts.parquet", "daily_forecasts.parquet", "metrics.json")
DAY_START, DAY_END = 6, 19
SERIES = {
    "actual": "ghi_actual",
    "p10": "ghi_p10",
    "p50": "ghi_p50",
    "p90": "ghi_p90",
    "nwp": "ghi_nwp",
    "persistence": "ghi_persistence",
    "clearsky": "ghi_clearsky",
}
DAILY = {"actual": "actual_kwh_m2", "p10": "p10_kwh_m2", "p50": "p50_kwh_m2", "p90": "p90_kwh_m2", "nwp": "nwp_kwh_m2"}


def load_contract(data_dir: Path) -> Dict[str, Any]:
    """Load and validate the four contract files from ``data_dir``."""
    missing = [f for f in CONTRACT_FILES if not (data_dir / f).exists()]
    if missing:
        raise FileNotFoundError(f"{data_dir}: missing contract file(s) {missing}")
    sites = json.loads((data_dir / "sites.json").read_text())
    forecasts = pd.read_parquet(data_dir / "forecasts.parquet")
    daily = pd.read_parquet(data_dir / "daily_forecasts.parquet")
    metrics = json.loads((data_dir / "metrics.json").read_text())
    validate_sites(sites)
    validate_forecasts(forecasts)
    validate_daily(daily)
    validate_metrics(metrics, [s["site_id"] for s in sites])
    return {"sites": sites, "forecasts": forecasts, "daily": daily, "metrics": metrics}


def publish_run(run_dir: Path, dashboard_dir: Path = DASHBOARD_DATA_DIR, frontend_dir: Path = FRONTEND_DATA_DIR,
                reports_dir: Path = REPORTS_DIR) -> None:
    load_contract(run_dir)  # validate before touching the dashboards
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    for f in CONTRACT_FILES:
        shutil.copy2(run_dir / f, dashboard_dir / f)
    logger.info(f"Published {run_dir.name} to {dashboard_dir}")

    reports_dir.mkdir(parents=True, exist_ok=True)
    for f in sorted((run_dir / "reports").glob("*.md")):
        shutil.copy2(f, reports_dir / f.name)
    shutil.copy2(run_dir / "metrics.json", reports_dir / "metrics.json")
    (reports_dir / "PUBLISHED_RUN").write_text(run_dir.name + "\n")

    # Small provenance files travel with the published numbers so they are versioned in git.
    prov = reports_dir / "published_run"
    prov.mkdir(exist_ok=True)
    for f in ("config.json", "environment.json", "data_manifest.json", "features.json", "quality.json"):
        if (run_dir / f).exists():
            shutil.copy2(run_dir / f, prov / f)
    shutil.copy2(run_dir / "model" / "forecaster.json", prov / "forecaster.json")

    export_frontend(dashboard_dir, frontend_dir)


def _clean(v: Any, digits: int = 1) -> Any:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return round(float(v), digits)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")))


def export_frontend(data_dir: Path = DASHBOARD_DATA_DIR, out_dir: Path = FRONTEND_DATA_DIR) -> None:
    """Derive the React app's static JSON from validated contract files."""
    c = load_contract(data_dir)
    sites, metrics = c["sites"], c["metrics"]
    test = c["forecasts"][c["forecasts"]["split"] == "test"]
    daily = c["daily"][c["daily"]["split"] == "test"].set_index(["site_id", "date"])

    months = sorted(metrics["by_month"])
    monthly = {
        "months": months,
        "overall": {k: [metrics["by_month"][m]["overall"].get(k) for m in months] for k in ("ml_model_p50", "raw_nwp", "persistence")},
        "by_site": {s["site_id"]: [metrics["by_month"][m]["by_site"].get(s["site_id"]) for m in months] for s in sites},
    }

    hours: List[int] = list(range(DAY_START, DAY_END + 1))
    day_rows = test[(test["hour_ist"] >= DAY_START) & (test["hour_ist"] <= DAY_END)]
    for site_id, sf in day_rows.groupby("site_id"):
        days = {}
        for date, dd in sf.groupby("date"):
            dd = dd.set_index("hour_ist").reindex(hours)
            conf = dd["confidence"].dropna()
            entry: Dict[str, Any] = {"confidence": conf.iloc[0] if not conf.empty else None}
            for key, col in SERIES.items():
                entry[key] = [_clean(v) for v in dd[col]]
            entry["daylight"] = [bool(v) if v == v else False for v in dd["is_daylight"]]
            drow = daily.loc[(site_id, date)]
            entry["daily"] = {k: _clean(drow[col], 3) for k, col in DAILY.items()}
            days[date] = entry
        _write_json(out_dir / "forecasts" / f"{site_id}.json", {"site_id": site_id, "hours": hours, "days": days})

    _write_json(out_dir / "sites.json", sites)
    _write_json(out_dir / "metrics.json", metrics)
    _write_json(out_dir / "monthly.json", monthly)
    logger.info(f"Exported frontend data for {len(sites)} sites, {len(months)} months -> {out_dir}")
