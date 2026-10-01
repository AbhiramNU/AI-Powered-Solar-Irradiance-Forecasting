# SuryaCast — React frontend

React + TypeScript (Vite) version of the SuryaCast Streamlit dashboard, in a green-on-white renewable theme.

## Pages

| Route | Page | Streamlit equivalent |
|---|---|---|
| `/` | Overview — headline KPIs and page directory | `app.py` |
| `/forecast` | 01 Forecast View — hourly P10/P50/P90 vs actual, raw NWP, persistence, clear-sky; cloudy-day explorer; chart/table toggle | `pages/1_Forecast_View.py` |
| `/accuracy` | 02 Accuracy Scorecard — model vs baselines, MAE/RMSE bars, monthly trend, coverage calibration, MAE by confidence level | `pages/2_Accuracy_Scorecard.py` |
| `/locations` | 03 Location Comparison — sortable site table, map, per-site model vs baselines, site × month error heatmap | `pages/3_Location_Comparison.py` |
| `/energy` | 04 Energy Estimate — kWh for a given capacity and performance ratio | `pages/4_Energy_Estimate.py` |
| `/method` | 05 Data & Method — methodology, pipeline diagram, limitations, licensing | `pages/5_Data_and_Method.py` |

Site and date selections live in the URL (`?site=JDH&date=2026-07-22`), so they carry over between Forecast and Energy and can be shared as links.

## Data

The frontend reads static JSON produced from the frozen output contract (`../data/sites.json`, `forecasts.parquet`, `metrics.json` — see `../docs/output_contract.md`). Regenerate it whenever the pipeline outputs change:

```bash
python ../scripts/export_frontend_data.py
```

This writes `public/data/` with `sites.json`, `metrics.json`, `monthly.json` (test-period monthly MAE, same all-hours convention as `metrics.json`), and `forecasts/<SITE>.json` (test-period, 06:00–19:00 IST hourly rows).

## Run

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # production build in dist/
npm run lint
```

The build is a static single-page app; when hosting it, configure the server to fall back to `index.html` for unknown paths so client-side routes work on reload.
