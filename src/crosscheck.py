"""
Independent cross-check of ERA5 GHI against NASA POWER (satellite-derived, SYN1DEG).

NASA POWER hourly stamps are UTC but its interval labelling (start vs end of hour) is not
assumed: the offset that maximises daylight correlation is searched and reported. Agreement
is then judged on hourly correlation and on daily totals, so a time shift cannot hide
behind daily sums.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

LAGS_H = np.arange(-3.0, 3.01, 0.5)


def align_nasa(site_frame: pd.DataFrame, nasa: pd.DataFrame, lag_h: float) -> pd.Series:
    """NASA POWER GHI on the canonical grid (``time_utc`` interval ends), using the detected stamp offset."""
    nasa_s = nasa.set_index(pd.DatetimeIndex(nasa["time"]).tz_convert("UTC"))["ALLSKY_SFC_SW_DWN"].astype(float)
    nasa_s.index = nasa_s.index + pd.Timedelta(hours=lag_h)
    nasa_s = nasa_s[~nasa_s.index.duplicated()]
    return pd.Series(nasa_s.reindex(pd.DatetimeIndex(site_frame["time_utc"])).to_numpy(), index=site_frame.index)


def compare_era5_nasa(site_frame: pd.DataFrame, nasa: pd.DataFrame,
                      min_corr: float = 0.9, max_abs_lag_h: float = 1.0, max_daily_diff_pct: float = 15.0) -> Dict[str, Any]:
    era5 = site_frame.set_index("time_utc")["ghi_actual"]
    daylight = site_frame.set_index("time_utc")["is_daylight"]
    nasa_s = nasa.set_index(pd.DatetimeIndex(nasa["time"]).tz_convert("UTC"))["ALLSKY_SFC_SW_DWN"].astype(float)

    def aligned(lag_h: float) -> pd.Series:
        shifted = nasa_s.copy()
        shifted.index = shifted.index + pd.Timedelta(hours=lag_h)
        union = shifted.index.union(era5.index)
        return shifted.reindex(union).interpolate(method="time", limit=1).reindex(era5.index)

    scores = {}
    for lag in LAGS_H:
        n = aligned(float(lag))
        ok = daylight & n.notna() & era5.notna()
        scores[float(lag)] = float(np.corrcoef(era5[ok], n[ok])[0, 1]) if ok.sum() > 100 else np.nan
    best = max((l for l in scores if not np.isnan(scores[l])), key=lambda l: scores[l])

    n = aligned(best)
    ok = daylight & n.notna() & era5.notna()
    diff = n[ok] - era5[ok]

    frame = pd.DataFrame({"era5": era5, "nasa": n, "date": site_frame.set_index("time_utc")["date"]})
    complete = frame.groupby("date").filter(lambda g: g[["era5", "nasa"]].notna().all().all())
    daily = complete.groupby("date")[["era5", "nasa"]].sum()
    daily = daily[daily["era5"] > 0]
    daily_diff_pct = float((np.abs(daily["nasa"] - daily["era5"]) / daily["era5"]).mean() * 100) if len(daily) else np.nan

    agreed = scores[best] >= min_corr and abs(best) <= max_abs_lag_h and daily_diff_pct <= max_daily_diff_pct
    return {
        "best_lag_hours": best,
        "lag_meaning": "NASA stamp + lag = ERA5 interval end; +1 means NASA labels the start of the hour",
        "hourly_correlation": round(scores[best], 4),
        "correlation_at_zero_lag": round(scores.get(0.0, np.nan), 4),
        "hourly_mae_wm2": round(float(diff.abs().mean()), 2),
        "hourly_bias_wm2": round(float(diff.mean()), 2),
        "daily_mean_abs_diff_pct": round(daily_diff_pct, 2),
        "days_compared": int(len(daily)),
        "status": "AGREED" if agreed else "FLAGGED",
    }
