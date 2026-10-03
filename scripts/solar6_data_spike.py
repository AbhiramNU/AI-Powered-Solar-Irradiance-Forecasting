"""
SOLAR-6 — Data availability spike.

One-week test pull for every site from the three sources (pinned ECMWF IFS day-ahead
forecast, ERA5, NASA POWER). Validates each response, saves sample parquet files and
writes reports/data_availability.md and reports/solar6_results.json.

Everything the report states is computed from this one-week pull. Full-period coverage is
reported by the pipeline (`python -m src.pipeline run` → reports/data_quality.md).

Usage:
    python -m scripts.solar6_data_spike
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any, Callable, Dict, List

import pandas as pd

from src.config import (
    DATA_AVAILABILITY_REPORT,
    REQUIRED_FORECAST_VARIABLES,
    SAMPLES_DATA_DIR,
    SOLAR6_RESULTS_JSON,
    VARIABLE_NAME_MAP,
    load_run_config,
)
from src.data.nasa_power import fetch_nasa_power_ghi
from src.data.open_meteo_era5 import fetch_era5_ghi
from src.data.open_meteo_previous_runs import fetch_previous_run
from src.data.sites import load_and_validate_sites
from src.data.validation import validate_api_dataframe

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

START_DATE = "2026-01-05"
END_DATE = "2026-01-11"


def _status(passed: int, total: int) -> str:
    if passed == total:
        return "PASS"
    return "PARTIAL" if passed > 0 else "BLOCKED"


def run_spike() -> Dict[str, Any]:
    """Run the SOLAR-6 data availability spike."""
    SAMPLES_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_AVAILABILITY_REPORT.parent.mkdir(parents=True, exist_ok=True)

    sites = load_and_validate_sites()
    cfg = load_run_config()
    primary_model = cfg.nwp_models[cfg.nwp_primary]

    sources: Dict[str, Dict[str, Any]] = {
        "previous_runs": {
            "endpoint": f"Open-Meteo Previous Runs ({primary_model})",
            "expected": ["time"] + REQUIRED_FORECAST_VARIABLES,
            "fetch": lambda s: fetch_previous_run(s["latitude"], s["longitude"], START_DATE, END_DATE, model=primary_model),
        },
        "era5": {
            "endpoint": "Open-Meteo ERA5 Archive (era5)",
            "expected": ["time", "shortwave_radiation"],
            "fetch": lambda s: fetch_era5_ghi(s["latitude"], s["longitude"], START_DATE, END_DATE),
        },
        "nasa_power": {
            "endpoint": "NASA POWER Hourly Point (UTC)",
            "expected": ["time", "ALLSKY_SFC_SW_DWN"],
            "fetch": lambda s: fetch_nasa_power_ghi(s["latitude"], s["longitude"], START_DATE, END_DATE),
        },
    }

    api_test_results: Dict[str, Dict[str, Any]] = {}
    passed = {k: 0 for k in sources}
    frames: Dict[str, List[pd.DataFrame]] = {k: [] for k in sources}

    for key, src in sources.items():
        fetch: Callable[[Dict[str, Any]], pd.DataFrame] = src["fetch"]
        for site in sites:
            rid = f"{key}_{site['site_id']}"
            try:
                df = fetch(site)
                val = validate_api_dataframe(df, f"{src['endpoint']} - {site['name']}", src["expected"], START_DATE, END_DATE)
                df.to_parquet(SAMPLES_DATA_DIR / f"{site['name'].lower()}_{key}.parquet", index=False)
                frames[key].append(df)
                missing = int(sum(v for c, v in val["missing_values"].items() if c != "time"))
                status = "PASS" if val["valid"] else "FAIL"
                passed[key] += status == "PASS"
                api_test_results[rid] = {"site": site["name"], "endpoint": src["endpoint"], "rows": len(df),
                                         "cols": len(df.columns), "missing_values": missing, "status": status,
                                         "issues": val["issues"]}
            except Exception as err:  # report any failure; the spike's job is to record availability
                api_test_results[rid] = {"site": site["name"], "endpoint": src["endpoint"], "status": "FAIL", "error": str(err)}
            logger.info(f"{rid}: {api_test_results[rid]['status']}")

    var_results: Dict[str, Dict[str, Any]] = {}
    prev = pd.concat(frames["previous_runs"]) if frames["previous_runs"] else pd.DataFrame()
    for var in REQUIRED_FORECAST_VARIABLES:
        present = var in prev.columns
        null_frac = float(prev[var].isna().mean()) if present and len(prev) else 1.0
        var_results[var] = {
            "name": VARIABLE_NAME_MAP.get(var, var),
            "raw_var": var,
            "primary_source": sources["previous_runs"]["endpoint"],
            "available": present and null_frac < 1.0,
            "missing_fraction": round(null_frac, 4),
            "status": "PASS" if present and null_frac == 0 else ("PARTIAL" if present and null_frac < 1 else "FAIL"),
        }

    statuses = {k: _status(passed[k], len(sites)) for k in sources}
    if all(s == "PASS" for s in statuses.values()):
        overall = "PASS"
    elif statuses["previous_runs"] != "BLOCKED" and statuses["era5"] != "BLOCKED":
        overall = "PARTIAL"
    else:
        overall = "BLOCKED"

    generate_markdown_report(sites, var_results, api_test_results, overall)

    json_data = {
        "date": date.today().isoformat(),
        "sites": sites,
        "sources": [{"name": src["endpoint"], "status": statuses[k], "sites_passed": passed[k], "sites_tested": len(sites)}
                    for k, src in sources.items()],
        "variables": list(var_results.values()),
        "test_period": {"start": START_DATE, "end": END_DATE},
        "overall_status": overall,
    }
    with open(SOLAR6_RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    logger.info(f"Overall: {overall}")
    return json_data


def generate_markdown_report(
    sites: List[Dict[str, Any]],
    var_results: Dict[str, Any],
    api_test_results: Dict[str, Any],
    overall_status: str,
) -> None:
    """Write reports/data_availability.md from the spike's measured results."""
    lines = [
        "# SOLAR-6 — Data Availability Report",
        "",
        f"**Generated:** {date.today().isoformat()} by `python -m scripts.solar6_data_spike`  ",
        f"**Test pull:** {START_DATE} → {END_DATE}  ",
        f"**Overall status:** `{overall_status}`",
        "",
        "This report covers a one-week pull only. Coverage of the full training and test period is measured by the",
        "pipeline and reported in `reports/data_quality.md`.",
        "",
        "## 1. Sites",
        "",
        "| Site ID | Site Name | Latitude | Longitude | Altitude (m) | Climate Zone |",
        "|---|---|---:|---:|---:|---|",
    ]
    for site in sites:
        lines.append(f"| `{site['site_id']}` | {site['name']} | {site['latitude']:.4f} | {site['longitude']:.4f} | "
                     f"{site.get('altitude_m', '')} | {site['climate_zone']} |")

    lines += ["", "## 2. Forecast variables (test week)", "",
              "| Variable | Source | Missing in test week | Status |", "|---|---|---:|---|"]
    for info in var_results.values():
        lines.append(f"| {info['name']} (`{info['raw_var']}`) | {info['primary_source']} | "
                     f"{info['missing_fraction'] * 100:.1f}% | `{info['status']}` |")

    lines += ["", "## 3. API test results", "",
              "| Source | Site | Rows | Columns | Missing values | Status |", "|---|---|---:|---:|---:|---|"]
    for res in api_test_results.values():
        if "error" in res:
            lines.append(f"| {res['endpoint']} | {res['site']} | – | – | – | `FAIL`: {res['error']} |")
        else:
            lines.append(f"| {res['endpoint']} | {res['site']} | {res['rows']} | {res['cols']} | {res['missing_values']} | `{res['status']}` |")

    issues = [(r["endpoint"], r["site"], i) for r in api_test_results.values() for i in r.get("issues", [])]
    if issues:
        lines += ["", "### Validation issues", ""] + [f"- {e} / {s}: {i}" for e, s, i in issues]

    lines += [
        "",
        "## 4. Known limitations",
        "",
        "- ERA5 and NASA POWER are modelled or satellite-derived, not ground pyranometer measurements.",
        "- ERA5 comes from the ECMWF IFS model family, the same family as the primary forecast input.",
        "",
    ]
    with open(DATA_AVAILABILITY_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    logger.info(f"Generated data availability report: {DATA_AVAILABILITY_REPORT}")


if __name__ == "__main__":
    run_spike()
