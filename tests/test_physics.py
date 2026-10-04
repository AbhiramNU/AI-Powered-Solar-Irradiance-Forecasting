"""Solar geometry and clear-sky checks."""

import numpy as np
import pandas as pd
import pytest

from src.physics import clear_sky_index, hourly_solar_geometry, solar_noon_utc

JODHPUR = {"site_id": "JDH", "name": "Jodhpur", "latitude": 26.2389, "longitude": 73.0243, "altitude_m": 231}


def _day(site, date="2025-03-10"):
    ends = pd.date_range(f"{date} 00:30", periods=24, freq="h", tz="Asia/Kolkata")  # midpoints on the IST hour
    geo = hourly_solar_geometry(ends, site)
    geo.index = ends - pd.Timedelta(minutes=30)
    return geo


def test_solar_noon_matches_longitude_and_equation_of_time():
    # Jodhpur is ~9.5° west of the IST meridian (82.5°E): ~38 min late, plus ~10 min equation of time in March.
    noon = solar_noon_utc(JODHPUR, "2025-03-10").tz_convert("Asia/Kolkata")
    assert pd.Timestamp("2025-03-10 12:40", tz="Asia/Kolkata") <= noon <= pd.Timestamp("2025-03-10 12:55", tz="Asia/Kolkata")


def test_clear_sky_peaks_near_solar_noon_and_is_zero_at_night():
    geo = _day(JODHPUR)
    assert geo["ghi_clearsky"].idxmax().hour in (12, 13)
    assert geo.loc[geo.index.hour <= 4, "ghi_clearsky"].eq(0).all()
    assert geo.loc[geo.index.hour >= 21, "ghi_clearsky"].eq(0).all()
    assert (geo["ghi_clearsky"] <= geo["ghi_extra"] + 1e-6).all()


def test_morning_and_evening_are_symmetric_about_solar_noon():
    geo = _day(JODHPUR, "2025-06-21")
    noon = solar_noon_utc(JODHPUR, "2025-06-21").tz_convert("Asia/Kolkata")
    centre = noon.hour + noon.minute / 60
    hours = geo.index.hour.to_numpy() + 0.0
    weights = geo["ghi_clearsky"].to_numpy()
    assert abs(np.average(hours, weights=weights) - centre) < 0.15


def test_altitude_increases_clear_sky_irradiance():
    low = _day({**JODHPUR, "altitude_m": 0})["ghi_clearsky"].max()
    high = _day({**JODHPUR, "altitude_m": 2500})["ghi_clearsky"].max()
    assert high > low


def test_naive_timestamps_are_rejected():
    with pytest.raises(ValueError, match="tz-aware"):
        hourly_solar_geometry(pd.date_range("2025-01-01", periods=3, freq="h"), JODHPUR)


def test_clear_sky_index_is_nan_outside_daylight_and_capped():
    kt = clear_sky_index(np.array([0.0, 500.0, 900.0, np.nan]), np.array([0.0, 500.0, 400.0, 600.0]),
                         np.array([False, True, True, True]))
    assert np.isnan(kt[0]) and kt[1] == pytest.approx(1.0) and kt[2] == pytest.approx(1.5) and np.isnan(kt[3])
