import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_sample_data():
    # 1. Generate sites.json
    sites = {
        "sites": [
            {"site_id": "site_01", "name": "Jodhpur", "latitude": 26.2389, "longitude": 73.0243, "climate_zone": "Arid"},
            {"site_id": "site_02", "name": "Bhadla", "latitude": 27.5385, "longitude": 71.9161, "climate_zone": "Arid"},
            {"site_id": "site_03", "name": "Pavagada", "latitude": 14.2833, "longitude": 77.2667, "climate_zone": "Semi-Arid"},
            {"site_id": "site_04", "name": "Kurnool", "latitude": 15.8281, "longitude": 78.0373, "climate_zone": "Tropical Savanna"},
            {"site_id": "site_05", "name": "Kamuthi", "latitude": 9.3361, "longitude": 78.3889, "climate_zone": "Tropical Monsoon"}
        ]
    }
    with open("solar-irradiance-poc/data/sample/sites.json", "w") as f:
        json.dump(sites, f, indent=2)

    # 2. Generate forecasts.parquet
    dates = pd.date_range(start="2026-01-01", end="2026-01-10", freq="D")
    hours = range(6, 20) # 6 to 19 (14 hours)
    
    rows = []
    for site in sites["sites"]:
        for date in dates:
            for hour in hours:
                date_str = date.strftime("%Y-%m-%d")
                # Create a bell curve shape for GHI
                peak_hour = 12.5
                intensity = np.exp(-0.5 * ((hour - peak_hour) / 2.5)**2)
                
                base_ghi = intensity * 800 + np.random.normal(0, 20)
                base_ghi = max(0, base_ghi)
                
                # Introduce a cloudy day
                if date_str == "2026-01-05":
                    base_ghi = base_ghi * 0.4 + np.random.normal(0, 50)
                    base_ghi = max(0, base_ghi)
                
                ghi_p50 = base_ghi
                ghi_p10 = max(0, ghi_p50 * 0.8)
                ghi_p90 = ghi_p50 * 1.2
                ghi_actual = ghi_p50 + np.random.normal(0, 40)
                ghi_actual = max(0, ghi_actual)
                ghi_nwp = ghi_p50 + np.random.normal(0, 60)
                ghi_nwp = max(0, ghi_nwp)
                ghi_clearsky = intensity * 900
                ghi_persistence = ghi_actual # mock
                
                rows.append({
                    "site_id": site["site_id"],
                    "date": date_str,
                    "hour_ist": hour,
                    "ghi_actual": float(ghi_actual),
                    "ghi_p10": float(ghi_p10),
                    "ghi_p50": float(ghi_p50),
                    "ghi_p90": float(ghi_p90),
                    "ghi_nwp": float(ghi_nwp),
                    "ghi_persistence": float(ghi_persistence),
                    "ghi_clearsky": float(ghi_clearsky),
                    "confidence": np.random.choice(["High", "Medium", "Low"]),
                    "split": "test"
                })
    
    df = pd.DataFrame(rows)
    df.to_parquet("solar-irradiance-poc/data/sample/forecasts.parquet")

    # 3. Generate metrics.json
    metrics = {
        "overall": {
            "MAE": 45.2,
            "RMSE": 60.5,
            "nRMSE": 8.5,
            "bias": -2.1,
            "skill_vs_persistence": 25.4,
            "skill_vs_raw_nwp": 18.2,
            "P10_P90_coverage": 82.5
        },
        "by_site": {
            site["site_id"]: {
                "MAE": 40 + np.random.normal(0, 5),
                "RMSE": 55 + np.random.normal(0, 5),
                "skill_vs_raw_nwp": 15 + np.random.normal(0, 5),
                "P10_P90_coverage": 80 + np.random.normal(0, 3)
            } for site in sites["sites"]
        },
        "by_month": {
            "2026-01": {
                "MAE": 46.1,
                "RMSE": 61.2
            }
        }
    }
    with open("solar-irradiance-poc/data/sample/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    generate_sample_data()
