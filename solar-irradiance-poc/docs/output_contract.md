# Output Contract

This document defines the frozen data contract between the ML prediction pipeline and the SuryaCast Streamlit dashboard.

The dashboard reads strictly from three files:
1. `sites.json`
2. `forecasts.parquet`
3. `metrics.json`

## 1. sites.json
Contains site metadata.

**Required fields:**
- `site_id` (string): Unique identifier for the site
- `name` (string): Human-readable name
- `latitude` (float): Latitude coordinate
- `longitude` (float): Longitude coordinate
- `climate_zone` (string): Climate zone description

**Example Record:**
```json
{
  "sites": [
    {
      "site_id": "site_01",
      "name": "Jodhpur",
      "latitude": 26.2389,
      "longitude": 73.0243,
      "climate_zone": "Arid"
    }
  ]
}
```

## 2. forecasts.parquet
Contains the hourly predictions and ground truth for the 2026 test period.

**Required columns:**
- `site_id` (string): matches site_id in sites.json
- `date` (string): YYYY-MM-DD
- `hour_ist` (int): 6 to 19
- `ghi_actual` (float): actual ERA5 GHI (W/m²)
- `ghi_p10` (float): 10th percentile prediction
- `ghi_p50` (float): median prediction
- `ghi_p90` (float): 90th percentile prediction
- `ghi_nwp` (float): raw weather-model GHI forecast
- `ghi_persistence` (float): persistence baseline
- `ghi_clearsky` (float): clear-sky GHI
- `confidence` (string): "High", "Medium", "Low", or null
- `split` (string): "train" or "test"

**Example Record (Conceptual):**
| site_id | date | hour_ist | ghi_actual | ghi_p10 | ghi_p50 | ghi_p90 | ghi_nwp | ghi_persistence | ghi_clearsky | confidence | split |
|---------|------------|----------|------------|---------|---------|---------|---------|-----------------|--------------|------------|-------|
| site_01 | 2026-01-05 | 12 | 800.0 | 750.0 | 810.0 | 850.0 | 790.0 | 780.0 | 900.0 | High | test |

## 3. metrics.json
Contains pre-calculated evaluation metrics for the test period.

**Required structure:**
The JSON can be nested (e.g. by overall, site, month) but must include key metrics dynamically read by the dashboard.

**Example Metrics Required:**
- `MAE`
- `RMSE`
- `nRMSE`
- `bias`
- `skill_vs_persistence`
- `skill_vs_raw_nwp`
- `P10_P90_coverage`

**Example Format:**
```json
{
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
    "site_01": {
      "MAE": 42.1,
      "skill_vs_raw_nwp": 15.0,
      "P10_P90_coverage": 81.0
    }
  }
}
```
