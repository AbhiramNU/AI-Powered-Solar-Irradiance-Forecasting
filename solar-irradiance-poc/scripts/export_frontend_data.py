"""Export the frozen output contract (sites.json, forecasts.parquet, metrics.json)
into static JSON consumed by the React frontend in ``frontend/``.

Usage:
    python scripts/export_frontend_data.py

Writes to ``frontend/public/data/``:
- sites.json              site metadata (list)
- metrics.json            copy of metrics.json
- monthly.json            test-period monthly MAE (overall and by site), derived
                          from forecasts.parquet using the same convention as
                          metrics.json (test split, all hours)
- forecasts/<SITE>.json   test-period daytime (06–19 IST) hourly forecasts per site
"""
import json
import math
import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIMARY_DATA_DIR = os.path.join(BASE_DIR, "data")
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "data", "sample")
OUT_DIR = os.path.join(BASE_DIR, "frontend", "public", "data")

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


def get_data_dir():
    if os.path.exists(os.path.join(PRIMARY_DATA_DIR, "forecasts.parquet")):
        return PRIMARY_DATA_DIR
    return SAMPLE_DATA_DIR


def clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return round(float(v), 1)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, separators=(",", ":"))


def main():
    data_dir = get_data_dir()

    with open(os.path.join(data_dir, "sites.json")) as f:
        sites = json.load(f)
    if isinstance(sites, dict):
        sites = sites.get("sites", [])
    with open(os.path.join(data_dir, "metrics.json")) as f:
        metrics = json.load(f)

    df = pd.read_parquet(os.path.join(data_dir, "forecasts.parquet"))
    test = df[df["split"] == "test"].copy()
    test["month"] = test["date"].str[:7]

    # Monthly MAE — same convention as metrics.json (test split, all hours)
    def mae(frame, col):
        return clean((frame[col] - frame["ghi_actual"]).abs().mean())

    months = sorted(test["month"].unique())
    monthly = {"months": months, "overall": {"ml_model_p50": [], "raw_nwp": [], "persistence": []}, "by_site": {}}
    for m in months:
        mf = test[test["month"] == m]
        monthly["overall"]["ml_model_p50"].append(mae(mf, "ghi_p50"))
        monthly["overall"]["raw_nwp"].append(mae(mf, "ghi_nwp"))
        monthly["overall"]["persistence"].append(mae(mf, "ghi_persistence"))
    for site_id, sf in test.groupby("site_id"):
        monthly["by_site"][site_id] = [mae(sf[sf["month"] == m], "ghi_p50") for m in months]

    # Per-site daytime hourly forecasts
    day = test[(test["hour_ist"] >= DAY_START) & (test["hour_ist"] <= DAY_END)]
    hours = list(range(DAY_START, DAY_END + 1))
    for site_id, sf in day.groupby("site_id"):
        days = {}
        for date, dd in sf.groupby("date"):
            dd = dd.set_index("hour_ist").reindex(hours)
            conf = dd["confidence"].dropna()
            entry = {"confidence": conf.iloc[0] if not conf.empty else None}
            for key, col in SERIES.items():
                entry[key] = [clean(v) for v in dd[col]]
            days[date] = entry
        write_json(os.path.join(OUT_DIR, "forecasts", f"{site_id}.json"),
                   {"site_id": site_id, "hours": hours, "days": days})

    write_json(os.path.join(OUT_DIR, "sites.json"), sites)
    write_json(os.path.join(OUT_DIR, "metrics.json"), metrics)
    write_json(os.path.join(OUT_DIR, "monthly.json"), monthly)
    print(f"Exported {len(sites)} sites, {len(months)} months from {data_dir} -> {OUT_DIR}")


if __name__ == "__main__":
    main()
