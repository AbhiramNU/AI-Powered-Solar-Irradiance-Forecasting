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

## Deploy (Vercel)

`vercel.json` holds the build settings, the SPA fallback rewrite (so `/forecast` etc. survive a reload) and long-lived caching for hashed `/assets/*`.

1. In Vercel: **Add New → Project**, import the GitHub repo.
2. Set **Root Directory** to `solar-irradiance-poc/frontend` (everything else is picked up from `vercel.json`).
3. Deploy. Pushes to the production branch redeploy automatically; other branches and PRs get preview URLs.

Or from the CLI, inside this folder: `npx vercel` (preview) / `npx vercel --prod`.

Vercel does not run the Python exporter — regenerate `public/data/` locally and commit it whenever pipeline outputs change.
