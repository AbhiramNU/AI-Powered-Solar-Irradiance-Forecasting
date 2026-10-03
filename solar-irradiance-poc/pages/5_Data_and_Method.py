import json
import os

import streamlit as st

LOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.png")
st.set_page_config(page_icon=LOGO, page_title="05 Method | SuryaCast", layout="wide")
st.logo(LOGO, size="large")
st.sidebar.caption("SuryaCast · a product of Sahasranshu Technologies")

st.markdown("""
<style>
    .brand-title { color: #d97706; font-size: 2rem; font-weight: bold; margin-bottom: 0; }
    .subtitle { color: #666; margin-top: 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="brand-title">SURYA CAST</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Data & Methodology</div>', unsafe_allow_html=True)
st.markdown("---")

metrics_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "metrics.json")
model_version = json.load(open(metrics_path)).get("model_version", "unknown") if os.path.exists(metrics_path) else "not published"

with st.expander("1. Problem statement", expanded=True):
    st.markdown("""
    Predict **next-day hourly Global Horizontal Irradiance (GHI)** for five Indian sites, with P10 / P50 / P90 values,
    using only information available the evening before. Dashboards show 06:00–19:00 IST; each hourly value is the
    mean over the hour centred on its label (12:00 = 11:30–12:30 IST).
    """)

with st.expander("2. Data sources", expanded=True):
    st.markdown("""
    - **Weather forecasts (model input)**: Open-Meteo Previous Runs API, day-ahead (`_previous_day1`) fields from three
      pinned models: **ECMWF IFS 0.25°** (primary), **GFS** and **ICON**. Pinning matters: Open-Meteo's `best_match`
      switches models over time.
    - **Reference "actual" (training target)**: **ERA5** reanalysis via the Open-Meteo archive, pinned to `era5`.
    - **Independent check**: **NASA POWER** hourly satellite-derived GHI (in UTC). Used only to check ERA5 and the forecasts.
    - **pvlib-python**: solar position and Ineichen clear-sky irradiance, averaged over each hour, with site altitude.

    All data are requested in UTC. Open-Meteo shifts data by whole hours when asked for IST, which mislabels hourly
    means by 30 minutes, so local labels are derived from UTC.

    *Privacy*: SuryaCast uses only public weather and reanalysis data. No personal data is collected.
    """)

with st.expander("3. Training, validation and test", expanded=True):
    st.markdown("""
    - **Train**: 2024. **Validation**: 2025, used for early stopping, blend weights, band calibration and confidence
      thresholds. **Test**: January–September 2026, scored once.
    - The final model is refit on 2024–2025 with every setting fixed beforehand.
    """)

with st.expander("4. Model approach", expanded=True):
    st.markdown(f"""
    - **LightGBM quantile regression** for P10, P50 and P90 (model `{model_version}`).
    - **Features** are all available at issue time: forecast GHI, direct/diffuse radiation, cloud cover, precipitation,
      temperature, humidity, pressure from each model, their clear-sky indices and spread, solar elevation, clear-sky GHI,
      day of year, hour and site. Observations are never used as features; the pipeline refuses to build one.
    - **P50** is blended with the raw ECMWF forecast per site; **P10–P90** is widened or narrowed per site to cover 80%
      of daylight hours on 2025.
    - **Confidence** labels come from forecast cloudiness and model disagreement only.
    """)

with st.expander("5. How accuracy is measured", expanded=True):
    st.markdown("""
    - Headline metrics use **daylight hours** only. At night every model is trivially right, which would halve the error.
    - **Skill** is the % reduction in MAE against the raw weather forecast, with a 95% bootstrap interval over days.
    - **Persistence** is idealised: it uses yesterday's ERA5, which is published days later.
    - Daily P10/P90 are calibrated for daily totals; adding up hourly P10s would overstate the range.
    """)

with st.expander("6. Limitations", expanded=True):
    st.markdown("""
    - ERA5 and NASA POWER are modelled or satellite-derived, not ground pyranometer measurements.
    - ERA5 is produced with the ECMWF IFS model family, like the primary forecast input. Part of the model's gain
      against ERA5 is learning ERA5's systematic differences from the forecast; the Accuracy page shows the
      independent NASA POWER check.
    - Each forecast hour comes from the model run made about 24 hours earlier, which approximates an evening issue time.
    """)

with st.expander("7. Source attribution & licensing", expanded=True):
    st.markdown("""
    - **Open-Meteo**: data under CC-BY 4.0 (ECMWF, NOAA GFS, DWD ICON, Copernicus ERA5).
    - **NASA POWER**: NASA Langley Research Center POWER Project.
    - **pvlib-python**: BSD 3-Clause License.
    """)

st.caption("SuryaCast is a product of Sahasranshu Technologies Private Limited | Rodic InfraAI Innovation Challenge 2026")
