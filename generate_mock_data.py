import json
import pandas as pd
import numpy as np

def generate_sample_data():
    # 1. Generate sites.json using official sprint sites
    sites = {
        "sites": [
            {"site_id": "JDH", "name": "Jodhpur", "latitude": 26.2389, "longitude": 73.0243, "climate_zone": "Hot semi-arid"},
            {"site_id": "DEL", "name": "Delhi", "latitude": 28.6139, "longitude": 77.2090, "climate_zone": "Composite"},
            {"site_id": "AMD", "name": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714, "climate_zone": "Hot semi-arid"},
            {"site_id": "NAG", "name": "Nagpur", "latitude": 21.1458, "longitude": 79.0882, "climate_zone": "Tropical wet/dry"},
            {"site_id": "CHE", "name": "Chennai", "latitude": 13.0827, "longitude": 80.2707, "climate_zone": "Tropical"}
        ]
    }
    with open("solar-irradiance-poc/data/sample/sites.json", "w") as f:
        json.dump(sites, f, indent=2)

    # 2. Generate forecasts.parquet
    dates = pd.date_range(start="2026-01-01", end="2026-01-10", freq="D")
    hours = range(6, 20)  # 6 to 19 (14 hours)
    
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
                ghi_persistence = ghi_actual  # mock
                
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
                "MAE": round(40 + float(np.random.normal(0, 5)), 1),
                "RMSE": round(55 + float(np.random.normal(0, 5)), 1),
                "skill_vs_raw_nwp": round(15 + float(np.random.normal(0, 5)), 1),
                "P10_P90_coverage": round(80 + float(np.random.normal(0, 3)), 1)
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
