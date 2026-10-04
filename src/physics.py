"""
Solar geometry and clear-sky irradiance.

All irradiance in this project is an hourly mean labelled with the END of its hour
(Open-Meteo convention). Geometry is therefore evaluated at the interval midpoint and
clear-sky GHI is averaged over sub-steps inside the interval, so that clear-sky index
``kt = GHI / GHI_clearsky`` compares like with like, including at sunrise and sunset.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
import pvlib

INTERVAL = pd.Timedelta(hours=1)


def _location(site: Dict[str, Any]) -> pvlib.location.Location:
    return pvlib.location.Location(
        latitude=float(site["latitude"]),
        longitude=float(site["longitude"]),
        altitude=float(site["altitude_m"]),
        tz="UTC",
        name=site.get("name"),
    )


def _as_utc_index(times: pd.Series | pd.DatetimeIndex) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(times)
    if idx.tz is None:
        raise ValueError("solar geometry needs tz-aware timestamps; got naive times")
    return idx.tz_convert("UTC")


def hourly_solar_geometry(
    interval_end: pd.Series | pd.DatetimeIndex,
    site: Dict[str, Any],
    substeps: int = 12,
) -> pd.DataFrame:
    """
    Solar geometry and clear-sky irradiance for hourly intervals ending at ``interval_end``.

    Returns a frame aligned with the input (same order, RangeIndex) with:
        solar_elevation, solar_zenith, solar_azimuth (degrees, at the interval midpoint),
        ghi_clearsky (W/m², Ineichen with monthly Linke turbidity and site altitude,
        averaged over ``substeps`` equally spaced instants inside the interval),
        ghi_extra (W/m², horizontal extraterrestrial irradiance, interval mean).
    """
    if substeps < 1:
        raise ValueError("substeps must be >= 1")
    end = _as_utc_index(interval_end)
    loc = _location(site)

    mid = end - INTERVAL / 2
    pos = loc.get_solarposition(mid)

    # Sub-step centres inside (end - 1h, end]: offsets (k + 0.5) / substeps of an hour.
    offsets = [INTERVAL * (k + 0.5) / substeps for k in range(substeps)]
    naive_end = end.tz_convert(None)
    sub_times = pd.DatetimeIndex(np.concatenate([(naive_end - INTERVAL + o).to_numpy() for o in offsets])).tz_localize("UTC")
    sub_pos = loc.get_solarposition(sub_times)
    sub_cs = loc.get_clearsky(sub_times, model="ineichen", solar_position=sub_pos)
    dni_extra = pvlib.irradiance.get_extra_radiation(sub_times)
    cos_zen = np.clip(np.cos(np.radians(sub_pos["apparent_zenith"].to_numpy())), 0.0, None)

    n = len(end)
    ghi_cs = np.clip(sub_cs["ghi"].to_numpy(), 0.0, None).reshape(substeps, n).mean(axis=0)
    ghi_extra = (np.asarray(dni_extra) * cos_zen).reshape(substeps, n).mean(axis=0)

    return pd.DataFrame({
        "solar_elevation": pos["apparent_elevation"].to_numpy(),
        "solar_zenith": pos["apparent_zenith"].to_numpy(),
        "solar_azimuth": pos["azimuth"].to_numpy(),
        "ghi_clearsky": ghi_cs,
        "ghi_extra": ghi_extra,
    })


def clear_sky_index(ghi: pd.Series | np.ndarray, ghi_clearsky: pd.Series | np.ndarray, daylight: np.ndarray, cap: float = 1.5) -> np.ndarray:
    """kt = GHI / clear-sky GHI on daylight rows (clipped to [0, cap]); NaN elsewhere or where GHI is NaN."""
    ghi = np.asarray(ghi, dtype=float)
    cs = np.asarray(ghi_clearsky, dtype=float)
    out = np.full(len(ghi), np.nan)
    ok = np.asarray(daylight, dtype=bool) & (cs > 0)
    out[ok] = np.clip(ghi[ok] / cs[ok], 0.0, cap)
    out[np.isnan(ghi)] = np.nan
    return out


def solar_noon_utc(site: Dict[str, Any], date: str) -> pd.Timestamp:
    """Time of solar transit for a UTC calendar date (used for alignment checks)."""
    loc = _location(site)
    day = pd.DatetimeIndex([pd.Timestamp(date, tz="UTC")])
    transit = pvlib.solarposition.sun_rise_set_transit_spa(day, loc.latitude, loc.longitude)["transit"].iloc[0]
    return pd.Timestamp(transit).tz_convert("UTC")
