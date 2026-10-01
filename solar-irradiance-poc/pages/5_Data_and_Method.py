import streamlit as st

st.set_page_config(page_title="05 Method | SuryaCast", layout="wide")

st.markdown("""
<style>
    .brand-title { color: #d97706; font-size: 2rem; font-weight: bold; margin-bottom: 0; }
    .subtitle { color: #666; margin-top: 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="brand-title">SURYA CAST</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Data & Methodology</div>', unsafe_allow_html=True)
st.markdown("---")

with st.expander("1. Problem Statement", expanded=True):
    st.markdown("""
    Solar power generation is inherently volatile due to cloud cover and weather changes. Accurate forecasting helps grid operators balance supply and demand. This PoC predicts the **next-day hourly Global Horizontal Irradiance (GHI)** during daylight hours (**06:00–19:00 IST**) across 5 Indian sites, generating P10, P50, and P90 confidence intervals.
    """)

with st.expander("2. Data Sources & Privacy", expanded=True):
    st.markdown("""
    We strictly use public, modeled, and satellite-derived meteorological data:
    - **Open-Meteo APIs**: Previous Runs, Historical Forecasts (GFS fallback), and ERA5 Historical Weather for ground truth.
    - **NASA POWER**: Supplemental hourly GHI data for cross-checking.
    - **pvlib-python**: Open-source library for solar position and clear-sky calculations.
    
    *Privacy Statement*: SuryaCast operates entirely on public weather and reanalysis data. No personal user data, proprietary plant schematics, or private commercial records are ingested or stored.
    """)

with st.expander("3. Training & Test Periods", expanded=True):
    st.markdown("""
    - **Training & Tuning Period**: January 2024 – December 2025
    - **Test Period**: January 2026 – September 2026
    
    *Note: The model is strictly evaluated on the unseen 2026 test period to ensure rigorous generalization.*
    """)

with st.expander("4. Model Approach", expanded=True):
    st.markdown("""
    The model uses an ensemble **LightGBM Quantile Regression** algorithm.
    - **Features**: Forecast GHI, low/mid/high cloud cover, temperature, relative humidity, sun elevation, clear-sky GHI, time embeddings, and the previous day's clear-sky index.
    - **Quantiles**: P10 (conservative 10th percentile), P50 (expected 50th percentile), and P90 (high-generation 90th percentile).
    - **Calibration**: Adjusted to target a 75%–85% P10-P90 coverage band.
    """)

with st.expander("5. Architecture Pipeline", expanded=True):
    st.markdown("""
    ```mermaid
    graph TD
        A[Weather & Solar Features] --> B[ML Model]
        B --> C[P10 / P50 / P90 Quantiles]
        C --> D[Daily Irradiation Aggregation]
        D --> E[Dashboard Visualization]
    ```
    """)

with st.expander("6. Limitations & Path to Production", expanded=True):
    st.markdown("""
    **Limitations**:
    - The PoC uses public modeled/satellite-derived data (ERA5/NASA POWER) as a proxy for ground truth, rather than actual plant sensor data.
    
    **Path to Production**:
    - Integrating real ground-sensor pyranometer data via a live telemetry ingestion pipeline.
    - Exploring recurrent neural networks (RNNs) or transformers to better capture temporal sequence dependencies.
    """)

with st.expander("7. Source Attribution & Licensing", expanded=True):
    st.markdown("""
    - **Open-Meteo**: Data provided under the CC-BY 4.0 license.
    - **NASA POWER**: Data obtained from the NASA Langley Research Center POWER Project.
    - **pvlib-python**: Provided under the BSD 3-Clause License.
    """)

st.caption("SuryaCast - Sahasranshu Technologies Private Limited | Rodic InfraAI Innovation Challenge 2026")
