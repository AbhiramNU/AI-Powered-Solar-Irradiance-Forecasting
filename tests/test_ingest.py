"""API clients and ingestion: pinned models, UTC handling, no silent fills or fallbacks."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import requests

from src.config import load_run_config
from src.data.nasa_power import fetch_nasa_power_ghi
from src.data.open_meteo_era5 import fetch_era5_ghi
from src.data.open_meteo_previous_runs import fetch_previous_run
from src.data.validation import DataQualityError
from src.ingest import ingest_site, utc_date_range, with_retries


def _response(payload):
    r = MagicMock()
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


@patch("requests.Session.get")
def test_previous_runs_pins_model_and_returns_tz_aware_times(get):
    get.return_value = _response({"hourly": {"time": ["2026-01-05T00:00", "2026-01-05T01:00"],
                                             "shortwave_radiation_previous_day1": [0.0, 10.0]}})
    df = fetch_previous_run(26.2, 73.0, "2026-01-05", "2026-01-05", variables=["shortwave_radiation_previous_day1"],
                            model="ecmwf_ifs025", timezone="GMT")
    assert get.call_args.kwargs["params"]["models"] == "ecmwf_ifs025"
    assert df["time"].dt.tz is not None
    assert df.attrs["model"] == "ecmwf_ifs025"


@patch("requests.Session.get")
def test_previous_runs_raises_when_required_variable_is_all_null(get):
    get.return_value = _response({"hourly": {"time": ["2026-01-05T00:00"], "a": [None], "b": [1.0]}})
    with pytest.raises(DataQualityError, match="no data for required"):
        fetch_previous_run(0, 0, "2026-01-05", "2026-01-05", variables=["a", "b"], required=["a"])


@patch("requests.Session.get")
def test_previous_runs_drops_all_null_optional_variable_instead_of_filling(get):
    get.return_value = _response({"hourly": {"time": ["2026-01-05T00:00", "2026-01-05T01:00"], "a": [1.0, None], "b": [None, None]}})
    df = fetch_previous_run(0, 0, "2026-01-05", "2026-01-05", variables=["a", "b"], required=["a"])
    assert "b" not in df.columns
    assert df.attrs["dropped_all_null"] == ["b"]
    assert np.isnan(df["a"].iloc[1])  # a partial gap stays missing


@patch("requests.Session.get")
def test_previous_runs_detects_missing_variable(get):
    get.return_value = _response({"hourly": {"time": ["2026-01-05T00:00"], "a": [1.0]}})
    with pytest.raises(ValueError, match="missing requested variable"):
        fetch_previous_run(0, 0, "2026-01-05", "2026-01-05", variables=["a", "b"])


@patch("requests.Session.get")
def test_previous_runs_missing_hourly_block(get):
    get.return_value = _response({"error": True, "reason": "No data"})
    with pytest.raises(ValueError, match="does not contain 'hourly' data block"):
        fetch_previous_run(0, 0, "2026-01-05", "2026-01-05")


@patch("requests.Session.get")
def test_era5_is_pinned_and_rejects_empty_series(get):
    get.return_value = _response({"hourly": {"time": ["2026-01-05T00:00"], "shortwave_radiation": [None]}})
    with pytest.raises(DataQualityError):
        fetch_era5_ghi(0, 0, "2026-01-05", "2026-01-05")
    assert get.call_args.kwargs["params"]["models"] == "era5"


@patch("requests.Session.get")
def test_nasa_requests_utc_and_parses_fill_values(get):
    get.return_value = _response({
        "header": {"time_standard": "UTC"},
        "properties": {"parameter": {"ALLSKY_SFC_SW_DWN": {"2025031006": 855.5, "2025031007": -999.0}}},
    })
    df = fetch_nasa_power_ghi(26.2, 73.0, "2025-03-10", "2025-03-10")
    assert get.call_args.kwargs["params"]["time-standard"] == "UTC"
    assert str(df["time"].dt.tz) == "UTC"
    assert df["time"].iloc[0] == pd.Timestamp("2025-03-10 06:00", tz="UTC")
    assert df["ALLSKY_SFC_SW_DWN"].iloc[0] == 855.5 and np.isnan(df["ALLSKY_SFC_SW_DWN"].iloc[1])


@patch("requests.Session.get")
def test_nasa_rejects_local_solar_time(get):
    get.return_value = _response({"header": {"time_standard": "LST"},
                                  "properties": {"parameter": {"ALLSKY_SFC_SW_DWN": {"2025031006": 1.0}}}})
    with pytest.raises(ValueError, match="expected UTC"):
        fetch_nasa_power_ghi(0, 0, "2025-03-10", "2025-03-10")


def test_retries_only_on_network_errors():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise requests.exceptions.ConnectionError("down")
        return pd.DataFrame({"x": [1]})

    assert len(with_retries(flaky, "x", attempts=3, backoff_s=0)) == 1

    def bad_data():
        raise DataQualityError("empty")

    with pytest.raises(DataQualityError):
        with_retries(bad_data, "x", attempts=3, backoff_s=0)


def test_ingestion_fails_instead_of_inventing_data(tmp_path, monkeypatch):
    def down(*a, **k):
        raise requests.exceptions.ConnectionError("down")

    monkeypatch.setattr("src.ingest.fetch_previous_run", down)
    monkeypatch.setattr("src.ingest.time.sleep", lambda s: None)
    site = {"site_id": "X", "latitude": 0.0, "longitude": 0.0}
    with pytest.raises(RuntimeError, match="failed after"):
        ingest_site(site, load_run_config(), raw_dir=tmp_path)
    assert not list(tmp_path.rglob("*.parquet"))


def test_utc_date_range_covers_local_period():
    start, end = utc_date_range(load_run_config())
    assert start == "2023-12-31" and end == "2026-09-30"
