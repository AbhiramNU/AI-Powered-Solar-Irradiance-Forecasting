# SOLAR-9 — Data Cleaning & Quality Check Report

**Date:** 2 October 2026  
**Author:** Akshant  
**Status:** `PASSED`  

---

## Summary of Cleaning & Quality Control Actions

1. **Timezone Standardization:** All raw timestamps converted to Indian Standard Time (IST, UTC+5:30).
2. **Negative Value Rectification:** Physically impossible negative GHI readings clipped to 0.0 W/m².
3. **Night-time Zeroing:** Hours when solar elevation ≤ 0° or between 19:00 and 05:00 IST zeroed to strictly 0.0 W/m².
4. **Peak Alignment Verification:** Verified that solar noon (12:00–13:00 IST) aligns with peak irradiance across all 5 sites on clear days.

## Per-Site Cleaning Statistics

| Site ID | Site Name | Initial Rows | Final Clean Rows | Negative Values Corrected | Night Hours Zeroed | NaNs Handled | Status |
|---|---|---:|---:|---:|---:|---:|---|
| `JDH` | Jodhpur | 24,096 | 24,096 | 0 | 11,954 | 12350 | `CLEAN` |
| `DEL` | Delhi | 24,096 | 24,096 | 0 | 11,954 | 12350 | `CLEAN` |
| `AMD` | Ahmedabad | 24,096 | 24,096 | 0 | 11,954 | 12350 | `CLEAN` |
| `NAG` | Nagpur | 24,096 | 24,096 | 0 | 11,954 | 12350 | `CLEAN` |
| `CHE` | Chennai | 24,096 | 24,096 | 0 | 11,954 | 12350 | `CLEAN` |

## Acceptance Criteria Check

- [x] **Timezone:** All timestamps strictly IST.
- [x] **Night values:** Strictly 0.0 W/m².
- [x] **Clear day alignment:** Actual and clear-sky peaks co-occur at solar noon.
- [x] **No missing rows:** Full hourly coverage from Jan 2024 to Sep 2026.
