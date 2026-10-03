# Evaluation Report

Model `suryacast-v2@20261003T142118Z-9b90130-dirty` · run `20261003T142118Z-9b90130-dirty` · test period 2026-01-01 → 2026-09-30

Headline metrics use daylight hours (interval-mean clear-sky GHI above the daylight threshold) of the test split, scored against ERA5. `skill` is the % reduction in MAE: ML vs raw NWP, raw NWP vs persistence. Persistence is idealised (uses yesterday's ERA5, which is not available at issue time).

## Headline (daylight hours, W/m²)

| Model | MAE | RMSE | nRMSE % | Bias | Skill % |
|---|---:|---:|---:|---:|---:|
| ML P50 (skill vs raw NWP) | 38.38 | 66.05 | 14.03 | +3.06 | +33.56 |
| Raw NWP (skill vs persistence) | 57.76 | 90.20 | 19.17 | +9.19 | +0.59 |
| Persistence (idealised) | 58.11 | 103.62 | 22.02 | +0.12 | +0.00 |

- Skill vs raw NWP: +33.56% with a 95% day-block bootstrap interval of [+31.24%, +35.93%]. The interval excludes zero, so the improvement over raw NWP, measured against ERA5, is supported.
- P10–P90 coverage: 81.84% of daylight hours (target 75–85%); quantile crossings: 0.
- Pinball loss: p10 10.63, p50 19.19, p90 7.08 W/m².
- All hours (for comparison only): ML MAE 19.47, raw NWP 28.74, persistence 29.20 W/m²; coverage 86.02%.
- Daily irradiation: ML MAE 0.300 kWh/m² (skill vs NWP +45.59%), daily P10–P90 coverage 80.37% over 1350 site-days.

## Independent check against NASA POWER (SYN1DEG, satellite-derived)

Neither the model nor its NWP input was fitted to this reference, so it shows whether the gain against ERA5 carries over.

| Forecast | MAE vs reference | Bias | Skill vs raw NWP % |
|---|---:|---:|---:|
| ML P50 | 53.05 | +34.94 | -3.51 |
| Raw NWP | 51.25 | +15.32 | |
| ERA5 itself | 53.95 | +31.03 | |

Against this reference the ML forecast does NOT beat raw NWP: its gain against ERA5 mostly reflects learning ERA5's systematic differences from the NWP input, not better prediction of measured sunlight. (10,617 daylight test hours.)

## By site (daylight hours)

| Site | ML MAE | Raw NWP MAE | Skill % | Skill interval | Coverage % |
|---|---:|---:|---:|---|---:|
| Jodhpur | 28.16 | 52.83 | +46.69 | [+41.62, +51.60] | 82.79 |
| Delhi | 45.69 | 66.78 | +31.57 | [+27.10, +36.02] | 84.23 |
| Ahmedabad | 30.36 | 53.02 | +42.74 | [+38.19, +46.79] | 81.17 |
| Nagpur | 43.12 | 66.03 | +34.69 | [+29.08, +39.59] | 78.26 |
| Chennai | 44.65 | 50.21 | +11.07 | [+7.02, +14.87] | 82.73 |

## By confidence level (daylight hours)

| Level | Site-days | MAE | Coverage % |
|---|---:|---:|---:|
| High | 405 | 13.00 | 79.35 |
| Medium | 553 | 34.21 | 82.02 |
| Low | 392 | 69.21 | 84.04 |

## Choices made on the validation year

- Blend weight with raw NWP (per site): {'AMD': 1.0, 'CHE': 0.8, 'DEL': 1.0, 'JDH': 1.0, 'NAG': 1.0}
- Band multiplier (per site): {'AMD': 1.26, 'CHE': 1.23, 'DEL': 1.45, 'JDH': 1.3, 'NAG': 1.16}
- Daily band multiplier: 0.61
- Confidence thresholds: [0.09, 0.2953]
- Trees after refit: {'p10': 732, 'p50': 750, 'p90': 662}
- Validation MAE by site: {'AMD': 29.756, 'CHE': 52.942, 'DEL': 38.977, 'JDH': 30.755, 'NAG': 39.628}; raw NWP: 59.07
- Validation coverage by site: {'AMD': 80.06, 'CHE': 80.1, 'DEL': 79.92, 'JDH': 80.14, 'NAG': 80.13}; daily: 79.73

## Features

Every feature is available when the forecast is issued; the pipeline refuses to build one derived from observations.

- **nwp** (50): `ec_shortwave_radiation`, `ec_direct_radiation`, `ec_diffuse_radiation`, `ec_cloud_cover`, `ec_precipitation`, `ec_temperature_2m`, `ec_relative_humidity_2m`, `ec_dew_point_2m`, `ec_pressure_msl`, `ec_kt`, `ec_dif_frac`, `gfs_shortwave_radiation`, `gfs_direct_radiation`, `gfs_diffuse_radiation`, `gfs_cloud_cover`, `gfs_precipitation`, `gfs_temperature_2m`, `gfs_relative_humidity_2m`, `gfs_dew_point_2m`, `gfs_cape`, `gfs_pressure_msl`, `gfs_kt`, `gfs_dif_frac`, `icon_shortwave_radiation`, `icon_direct_radiation`, `icon_diffuse_radiation`, `icon_cloud_cover`, `icon_precipitation`, `icon_temperature_2m`, `icon_relative_humidity_2m`, `icon_dew_point_2m`, `icon_pressure_msl`, `icon_kt`, `icon_dif_frac`, `ec_kt_m1`, `ec_kt_p1`, `ec_cloud_cover_m1`, `ec_cloud_cover_p1`, `ec_kt_m2`, `ec_kt_p2`, `ec_cloud_cover_m2`, `ec_cloud_cover_p2`, `ec_d_kt`, `gfs_d_kt`, `icon_d_kt`, `ec_d_kt_std`, `ec_d_cc`, `ec_d_precip`, `kt_mean`, `kt_spread`
- **geometry** (2): `solar_elevation`, `ghi_clearsky`
- **calendar** (3): `sin_doy`, `cos_doy`, `hour_ist`
- **site** (1): `site_code`
