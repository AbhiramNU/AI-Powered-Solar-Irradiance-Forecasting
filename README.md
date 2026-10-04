# Solar Irradiance Prediction PoC (SuryaCast)

Sahasranshu Technologies · Rodic InfraAI Innovation Challenge 2026

Predict next-day hourly Global Horizontal Irradiance (GHI) with P10 / P50 / P90 values for five Indian sites
from public weather forecasts, and show every prediction next to what happened.

## Quick start

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt        # exact versions used for the published run
python -m src.pipeline all             # ingest → dataset → train → evaluate → publish
python -m pytest                       # offline tests (live API test: pytest -m integration)
```

Stages can also be run one at a time:

| Command | What it does |
|---|---|
| `python -m src.pipeline ingest [--refresh]` | Download raw data to `data/raw/` (cached, recorded in `manifest.json`) |
| `python -m src.pipeline run` | Build the dataset, train, evaluate; writes `runs/<run_id>/` |
| `python -m src.pipeline publish [--run-id ID]` | Validate a run and copy it to the dashboards and `reports/` |
| `python -m src.pipeline contract-doc` | Regenerate `solar-irradiance-poc/docs/output_contract.md` |
| `python -m scripts.solar6_data_spike` | One-week live availability check (SOLAR-6) |

## How it works

| Stage | Module | Notes |
|---|---|---|
| Configuration | `config/run.json`, `config/sites.json`, `src/config.py` | Dates, splits, NWP models, hyperparameters, calibration targets, site altitude |
| Ingestion | `src/ingest.py`, `src/data/` | Day-ahead forecasts from pinned models (ECMWF IFS, GFS, ICON), ERA5 (pinned), NASA POWER. All requested in UTC. No fallback data: a failed download stops the pipeline. |
| Dataset | `src/dataset.py` | One hourly grid per site keyed by the UTC end of each hour; missing values stay missing; quality gates fail hard |
| Physics | `src/physics.py` | pvlib solar position at each interval's midpoint; Ineichen clear-sky averaged over the hour, with altitude |
| Features | `src/features.py` | Registered with their source; anything derived from observations is refused |
| Model | `src/model.py` | LightGBM quantile models; blend weight, band width, confidence thresholds and daily band chosen on 2025 only; refit on 2024–2025; saved as LightGBM text + JSON |
| Evaluation | `src/evaluate.py`, `src/crosscheck.py` | Daylight-hour metrics, pinball loss, day-block bootstrap intervals, daily totals, independent check against NASA POWER |
| Contract | `src/contract.py` | Schemas for the dashboard files, enforced on write and on publish |
| Reports | `src/reports.py` → `reports/` | Data quality and evaluation reports generated from computed results |

Time convention: each hourly value is the mean over the hour centred on its IST label (12:00 = 11:30–12:30 IST).
Open-Meteo shifts data by whole hours when asked for IST (UTC+5:30), which mislabels hourly means by 30 minutes,
so everything is fetched in UTC and labelled afterwards.

## Results and how to read them

See `reports/evaluation.md` (published run in `reports/PUBLISHED_RUN`, provenance in `reports/published_run/`).

- Against ERA5, the training target, the model's daylight MAE is about a third lower than the raw ECMWF forecast's.
- Against NASA POWER, which no part of the model was fitted to, the model is **not** better than the raw ECMWF forecast.
  Most of the gain against ERA5 comes from learning ERA5's systematic differences from the forecast (for example a
  monsoon-season bias), not from predicting sunlight better. A stronger claim needs an independent target such as
  ground measurements or a satellite product.
- Persistence uses yesterday's ERA5, which is published days later, so it is an idealised reference.

## Project structure

- `config/` — run configuration and sites
- `src/` — pipeline package (see table above)
- `scripts/` — the SOLAR-6 availability spike
- `data/raw/` — downloaded data (not committed); `data/samples/` — one-week samples from the spike
- `runs/` — one directory per pipeline run (not committed)
- `reports/` — reports and provenance for the published run
- `notebooks/` — exploratory analysis
- `tests/` — offline tests, including an end-to-end run on synthetic data
- `solar-irradiance-poc/` — SuryaCast dashboards (Streamlit, and React in `frontend/`)
- `doc/` — scope and sprint plan
