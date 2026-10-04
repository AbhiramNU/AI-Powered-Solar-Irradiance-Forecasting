"""Canonical dataset: UTC grid, no zero-filling, quality gates."""

import numpy as np
import pandas as pd
import pytest

from src.config import load_run_config
from src.data.validation import DataQualityError
from src.dataset import build_dataset
from tests.synthetic import TEST_SITES, make_run_config, write_raw


@pytest.fixture()
def built(tmp_path):
    write_raw(tmp_path / "raw", nwp_nan_rows=48)
    cfg = load_run_config(make_run_config(tmp_path))
    data, qc = build_dataset(TEST_SITES, cfg, tmp_path / "raw")
    return cfg, data, qc


def test_interval_midpoints_fall_on_the_local_hour(built):
    _, data, _ = built
    mid = data["time_utc"] - pd.Timedelta(minutes=30)
    local = mid.dt.tz_convert("Asia/Kolkata")
    assert (local.dt.minute == 0).all()
    assert (local.dt.hour == data["hour_ist"]).all()


def test_missing_nwp_stays_missing(built):
    _, data, _ = built
    first = data[data["site_id"] == "AAA"].sort_values("time_utc").head(48)
    assert first["ec_shortwave_radiation"].isna().all()
    assert not (data["ec_shortwave_radiation"] == 0).all()


def test_split_by_year_and_no_overlap(built):
    cfg, data, _ = built
    assert set(data.loc[data["year"] == 2024, "split"]) == {"train"}
    assert set(data.loc[data["year"] == 2025, "split"]) == {"validation"}
    assert set(data.loc[data["year"] == 2026, "split"]) == {"test"}


def test_persistence_uses_previous_day(built):
    _, data, _ = built
    s = data[data["site_id"] == "AAA"].set_index("time_utc")
    t = s[s["is_daylight"]].index[500]
    prev = s.loc[t - pd.Timedelta(hours=24)]
    if prev["is_daylight"]:
        expected = prev["ghi_actual"] / prev["ghi_clearsky"] * s.loc[t, "ghi_clearsky"]
        assert s.loc[t, "ghi_persistence"] == pytest.approx(min(expected, 1.5 * s.loc[t, "ghi_clearsky"]), rel=1e-6)


def test_quality_gate_rejects_missing_target(tmp_path):
    write_raw(tmp_path / "raw")
    path = tmp_path / "raw" / "era5" / "AAA.parquet"
    df = pd.read_parquet(path)
    df.loc[df.index[: len(df) // 3], "shortwave_radiation"] = np.nan
    df.to_parquet(path)
    cfg = load_run_config(make_run_config(tmp_path))
    with pytest.raises(DataQualityError, match="ERA5 target missing"):
        build_dataset(TEST_SITES, cfg, tmp_path / "raw")


def test_naive_raw_timestamps_are_rejected(tmp_path):
    write_raw(tmp_path / "raw")
    path = tmp_path / "raw" / "era5" / "AAA.parquet"
    df = pd.read_parquet(path)
    df["time"] = df["time"].dt.tz_localize(None)
    df.to_parquet(path)
    cfg = load_run_config(make_run_config(tmp_path))
    with pytest.raises(DataQualityError, match="not timezone-aware"):
        build_dataset(TEST_SITES, cfg, tmp_path / "raw")
