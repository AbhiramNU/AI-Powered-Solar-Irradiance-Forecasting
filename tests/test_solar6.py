"""
Unit tests for site configuration and the SOLAR-6 data availability spike.

Live API tests are marked with @pytest.mark.integration.
"""

import json

import pytest

from src.config import REQUIRED_FORECAST_VARIABLES, SITES_CONFIG_FILE, load_run_config
from src.data.sites import load_and_validate_sites
from src.data.validation import validate_api_dataframe
from scripts.solar6_data_spike import generate_markdown_report, run_spike


def test_sites_load_with_unique_ids_and_valid_coordinates():
    sites = load_and_validate_sites(SITES_CONFIG_FILE)
    assert {s["site_id"] for s in sites} == {"JDH", "DEL", "AMD", "NAG", "CHE"}
    for s in sites:
        assert -90 <= s["latitude"] <= 90 and -180 <= s["longitude"] <= 180 and 0 <= s["altitude_m"] < 1000


def test_site_validation_requires_altitude(tmp_path):
    f = tmp_path / "sites.json"
    f.write_text(json.dumps([{"site_id": "A", "name": "A", "latitude": 10, "longitude": 10, "climate_zone": "A"}]))
    with pytest.raises(ValueError, match="altitude_m"):
        load_and_validate_sites(f)


def test_site_validation_rejects_duplicates(tmp_path):
    site = {"site_id": "A", "name": "A", "latitude": 10, "longitude": 10, "altitude_m": 5, "climate_zone": "A"}
    f = tmp_path / "sites.json"
    f.write_text(json.dumps([site, {**site, "site_id": "B"}]))
    with pytest.raises(ValueError, match="Duplicate coordinates"):
        load_and_validate_sites(f)


def test_run_config_loads_and_splits_are_ordered():
    cfg = load_run_config()
    assert max(cfg.splits["train"]) < min(cfg.splits["validation"]) < min(cfg.splits["test"])
    assert cfg.nwp_primary in cfg.nwp_models
    assert "shortwave_radiation_previous_day1" in REQUIRED_FORECAST_VARIABLES
    assert "cloud_cover_previous_day1" in REQUIRED_FORECAST_VARIABLES


def test_validation_detects_duplicates_gaps_and_all_null_columns():
    import pandas as pd
    df = pd.DataFrame({
        "time": ["2026-01-05T00:00", "2026-01-05T00:00", "2026-01-05T03:00"],
        "shortwave_radiation": [0.0, 0.0, -5.0],
        "cloud_cover": [None, None, None],
    })
    res = validate_api_dataframe(df, "Test", ["time", "shortwave_radiation"])
    assert res["has_duplicates"] and res["has_gaps"]
    assert res["all_null_columns"] == ["cloud_cover"] and res["valid"] is False
    assert res["negative_values"]["shortwave_radiation"] == 1


def test_validation_flags_uncovered_date_range():
    import pandas as pd
    df = pd.DataFrame({"time": pd.date_range("2026-01-05", periods=24, freq="h"), "x": 1.0})
    res = validate_api_dataframe(df, "Test", ["time"], start_date="2026-01-05", end_date="2026-01-07")
    assert res["valid"] is False and any("does not cover" in i for i in res["issues"])


def test_report_states_only_measured_results(tmp_path, monkeypatch):
    report = tmp_path / "report.md"
    monkeypatch.setattr("scripts.solar6_data_spike.DATA_AVAILABILITY_REPORT", report)
    sites = [{"site_id": "JDH", "name": "Jodhpur", "latitude": 26.2389, "longitude": 73.0243, "altitude_m": 231, "climate_zone": "Hot semi-arid"}]
    var_results = {"v": {"name": "Forecast GHI", "raw_var": "v", "primary_source": "src", "available": True,
                         "missing_fraction": 0.25, "status": "PARTIAL"}}
    api = {"x": {"endpoint": "Previous Runs", "site": "Jodhpur", "rows": 168, "cols": 5, "missing_values": 3, "status": "PASS", "issues": []}}
    generate_markdown_report(sites, var_results, api, "PARTIAL")
    text = report.read_text()
    assert "25.0%" in text and "`PARTIAL`" in text
    assert "VERIFIED" not in text and "2016-01-01" not in text


@pytest.mark.integration
def test_live_api_pulls():
    data = run_spike()
    assert data["overall_status"] == "PASS"
