# SOLAR-6 — Data Availability Report

**Generated:** 2026-10-03 by `python -m scripts.solar6_data_spike`  
**Test pull:** 2026-01-05 → 2026-01-11  
**Overall status:** `PASS`

This report covers a one-week pull only. Coverage of the full training and test period is measured by the
pipeline and reported in `reports/data_quality.md`.

## 1. Sites

| Site ID | Site Name | Latitude | Longitude | Altitude (m) | Climate Zone |
|---|---|---:|---:|---:|---|
| `JDH` | Jodhpur | 26.2389 | 73.0243 | 231 | Hot semi-arid |
| `DEL` | Delhi | 28.6139 | 77.2090 | 216 | Composite |
| `AMD` | Ahmedabad | 23.0225 | 72.5714 | 53 | Hot semi-arid |
| `NAG` | Nagpur | 21.1458 | 79.0882 | 310 | Tropical wet/dry |
| `CHE` | Chennai | 13.0827 | 80.2707 | 6 | Tropical |

## 2. Forecast variables (test week)

| Variable | Source | Missing in test week | Status |
|---|---|---:|---|
| Forecast GHI (`shortwave_radiation_previous_day1`) | Open-Meteo Previous Runs (ecmwf_ifs025) | 0.0% | `PASS` |
| Total Cloud Cover (`cloud_cover_previous_day1`) | Open-Meteo Previous Runs (ecmwf_ifs025) | 0.0% | `PASS` |
| Temperature (`temperature_2m_previous_day1`) | Open-Meteo Previous Runs (ecmwf_ifs025) | 0.0% | `PASS` |
| Relative Humidity (`relative_humidity_2m_previous_day1`) | Open-Meteo Previous Runs (ecmwf_ifs025) | 0.0% | `PASS` |

## 3. API test results

| Source | Site | Rows | Columns | Missing values | Status |
|---|---|---:|---:|---:|---|
| Open-Meteo Previous Runs (ecmwf_ifs025) | Jodhpur | 168 | 5 | 0 | `PASS` |
| Open-Meteo Previous Runs (ecmwf_ifs025) | Delhi | 168 | 5 | 0 | `PASS` |
| Open-Meteo Previous Runs (ecmwf_ifs025) | Ahmedabad | 168 | 5 | 0 | `PASS` |
| Open-Meteo Previous Runs (ecmwf_ifs025) | Nagpur | 168 | 5 | 0 | `PASS` |
| Open-Meteo Previous Runs (ecmwf_ifs025) | Chennai | 168 | 5 | 0 | `PASS` |
| Open-Meteo ERA5 Archive (era5) | Jodhpur | 168 | 2 | 0 | `PASS` |
| Open-Meteo ERA5 Archive (era5) | Delhi | 168 | 2 | 0 | `PASS` |
| Open-Meteo ERA5 Archive (era5) | Ahmedabad | 168 | 2 | 0 | `PASS` |
| Open-Meteo ERA5 Archive (era5) | Nagpur | 168 | 2 | 0 | `PASS` |
| Open-Meteo ERA5 Archive (era5) | Chennai | 168 | 2 | 0 | `PASS` |
| NASA POWER Hourly Point (UTC) | Jodhpur | 168 | 2 | 0 | `PASS` |
| NASA POWER Hourly Point (UTC) | Delhi | 168 | 2 | 0 | `PASS` |
| NASA POWER Hourly Point (UTC) | Ahmedabad | 168 | 2 | 0 | `PASS` |
| NASA POWER Hourly Point (UTC) | Nagpur | 168 | 2 | 0 | `PASS` |
| NASA POWER Hourly Point (UTC) | Chennai | 168 | 2 | 0 | `PASS` |

## 4. Known limitations

- ERA5 and NASA POWER are modelled or satellite-derived, not ground pyranometer measurements.
- ERA5 comes from the ECMWF IFS model family, the same family as the primary forecast input.

