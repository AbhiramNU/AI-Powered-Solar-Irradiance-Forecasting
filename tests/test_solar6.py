"""
Automated unit tests for SOLAR-6 — Data Foundation / Data Availability Spike.

All unit tests use mocked API responses or local configuration.
Live integration tests are marked with @pytest.mark.integration.
"""

import json
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from src.config import REQUIRED_FORECAST_VARIABLES, SITES_CONFIG_FILE
from src.data.nasa_power import fetch_nasa_power_ghi
from src.data.open_meteo_era5 import fetch_era5_ghi
from src.data.open_meteo_previous_runs import fetch_previous_run
from src.data.sites import load_and_validate_sites
from src.data.validation import validate_api_dataframe
from scripts.solar6_data_spike import generate_markdown_report, run_spike


# 1. Test sites.json loads
def test_sites_json_exists_and_loads(tmp_path):
    sites = load_and_validate_sites(SITES_CONFIG_FILE)
    assert isinstance(sites, list)


# 2. Test exactly five sites exist
def test_exactly_five_sites_exist():
    sites = load_and_validate_sites(SITES_CONFIG_FILE)
    assert len(sites) == 5


# 3. Test site IDs are unique
def test_site_ids_are_unique():
    sites = load_and_validate_sites(SITES_CONFIG_FILE)
    site_ids = [s["site_id"] for s in sites]
    assert len(site_ids) == len(set(site_ids))


# 4. Test coordinates are valid
def test_coordinates_are_valid():
    sites = load_and_validate_sites(SITES_CONFIG_FILE)
    coords = []
    for site in sites:
        lat = site["latitude"]
        lon = site["longitude"]
        assert -90.0 <= lat <= 90.0
        assert -180.0 <= lon <= 180.0
        coords.append((lat, lon))
    assert len(coords) == len(set(coords))


def test_invalid_site_config_handling(tmp_path):
    invalid_file = tmp_path / "invalid_sites.json"

    # Test invalid count (< 5)
    invalid_file.write_text(json.dumps([{"site_id": "A", "name": "A", "latitude": 10, "longitude": 10, "climate_zone": "A"}]))
    with pytest.raises(ValueError, match="Expected exactly 5 sites"):
        load_and_validate_sites(invalid_file)


# 5. Test required variables are defined
def test_required_variables_defined():
    assert len(REQUIRED_FORECAST_VARIABLES) == 6
    assert "shortwave_radiation_previous_day1" in REQUIRED_FORECAST_VARIABLES
    assert "cloud_cover_low_previous_day1" in REQUIRED_FORECAST_VARIABLES
    assert "temperature_2m_previous_day1" in REQUIRED_FORECAST_VARIABLES


# 6. Test API response parser handles valid response (Mocked)
@patch("requests.Session.get")
def test_previous_runs_valid_response(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "hourly": {
            "time": ["2026-01-05T00:00", "2026-01-05T01:00"],
            "shortwave_radiation_previous_day1": [0.0, 10.0],
            "cloud_cover_low_previous_day1": [0.0, 5.0],
            "cloud_cover_mid_previous_day1": [0.0, 0.0],
            "cloud_cover_high_previous_day1": [0.0, 0.0],
            "temperature_2m_previous_day1": [20.0, 21.0],
            "relative_humidity_2m_previous_day1": [50.0, 48.0],
        }
    }
    mock_get.return_value = mock_resp

    df = fetch_previous_run(26.2389, 73.0243, "2026-01-05", "2026-01-05")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "shortwave_radiation_previous_day1" in df.columns


# 7. Test API parser detects missing hourly data
@patch("requests.Session.get")
def test_previous_runs_missing_hourly_data(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"error": True, "reason": "No data"}
    mock_get.return_value = mock_resp

    with pytest.raises(ValueError, match="does not contain 'hourly' data block"):
        fetch_previous_run(26.2389, 73.0243, "2026-01-05", "2026-01-05")


# 8. Test missing variables are detected
@patch("requests.Session.get")
def test_previous_runs_missing_variables(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "hourly": {
            "time": ["2026-01-05T00:00"],
            "shortwave_radiation_previous_day1": [0.0],
            # Missing other required variables
        }
    }
    mock_get.return_value = mock_resp

    with pytest.raises(ValueError, match="missing requested variable"):
        fetch_previous_run(26.2389, 73.0243, "2026-01-05", "2026-01-05")


# 9. Test duplicate timestamps are detected by validator
def test_validation_detects_duplicate_timestamps():
    df_dups = pd.DataFrame({
        "time": ["2026-01-05T00:00", "2026-01-05T00:00"],
        "shortwave_radiation_previous_day1": [0.0, 0.0],
    })
    res = validate_api_dataframe(df_dups, "Test", expected_columns=["time", "shortwave_radiation_previous_day1"])
    assert res["has_duplicates"] is True
    assert any("duplicate timestamp" in issue for issue in res["issues"])


def test_validation_detects_negative_irradiance():
    df_neg = pd.DataFrame({
        "time": ["2026-01-05T00:00", "2026-01-05T01:00"],
        "shortwave_radiation": [-5.0, 100.0],
    })
    res = validate_api_dataframe(df_neg, "Test", expected_columns=["time", "shortwave_radiation"])
    assert "shortwave_radiation" in res["negative_values"]
    assert res["negative_values"]["shortwave_radiation"] == 1


# 10. Test report generation works
def test_report_generation(tmp_path):
    report_file = tmp_path / "test_report.md"

    sites = [
        {"site_id": "JDH", "name": "Jodhpur", "latitude": 26.2389, "longitude": 73.0243, "climate_zone": "Hot semi-arid"}
    ]
    var_results = {
        "shortwave_radiation_previous_day1": {
            "name": "Forecast GHI",
            "raw_var": "shortwave_radiation_previous_day1",
            "primary_source": "Open-Meteo Previous Runs",
            "available": True,
            "first_available_date": "2016-01-01",
            "missing_values": 0,
            "fallback": "None required",
            "status": "PASS",
        }
    }
    api_results = {
        "prev_jdh": {"endpoint": "Previous Runs", "site": "Jodhpur", "rows": 168, "cols": 7, "status": "PASS"}
    }

    with patch("scripts.solar6_data_spike.DATA_AVAILABILITY_REPORT", report_file):
        generate_markdown_report(sites, var_results, api_results, "PASS")

    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "# SOLAR-6 — Data Availability Report" in content
    assert "Jodhpur" in content
    assert "Forecast GHI" in content


# Live integration test (marked as integration)
@pytest.mark.integration
def test_live_api_pulls():
    data = run_spike()
    assert data["overall_status"] == "PASS"
