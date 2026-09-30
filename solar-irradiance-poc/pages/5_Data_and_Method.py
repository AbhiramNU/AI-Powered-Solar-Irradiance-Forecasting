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
    Solar power generation is inherently volatile due to cloud cover and weather changes. Accurate forecasting helps grid operators balance supply and demand. This PoC predicts the next-day hourly Global Horizontal Irradiance (GHI) across 5 Indian sites, generating P10, P50, and P90 confidence intervals.
    """)

with st.expander("2. Data Sources", expanded=True):
    st.markdown("""
    We use public, modeled, and satellite-derived data:
    - **Open-Meteo Previous Runs API**: Day-ahead weather forecasts (Jan 2024 - Sep 2026).
    - **Open-Meteo Historical Forecast API (GFS)**: Fallback forecast data.
    - **Open-Meteo ERA5 Historical Weather API**: Ground truth for actual GHI.
    - **NASA POWER**: Hourly GHI for cross-checking.
    - **pvlib**: Solar position and clear-sky calculations.
    """)

with st.expander("3. Training & Test Periods", expanded=True):
    st.markdown("""
    - **Training Period**: January 2024 – December 2025
    - **Test Period**: January 2026 – September 2026
    
    *Note: The model is strictly evaluated on the unseen 2026 test period.*
    """)

with st.expander("4. Model Approach", expanded=True):
    st.markdown("""
    The model uses **LightGBM Quantile Regression** targeting the clear-sky index.
    - **Features**: Forecast GHI, low/mid/high cloud cover, temperature, relative humidity, sun elevation, clear-sky GHI, time embeddings, and previous day's clear-sky index.
    - **Quantiles**: P10 (0.1), P50 (0.5), and P90 (0.9).
    - **Calibration**: Adjusted on 2025 data to target roughly 80% P10-P90 coverage.
    """)

with st.expander("5. Architecture Diagram", expanded=True):
    st.markdown("""
    ```mermaid
    graph TD
        A[Public weather forecast] --> B[Feature engineering]
        B --> C[Clear-sky / solar features]
        C --> D[LightGBM quantile model]
        D --> E[P10 / P50 / P90 Predictions]
        E --> F[Calibration]
        F --> G[Dashboard Visualization]
    ```
    """)

with st.expander("6. Limitations & Path to Production", expanded=True):
    st.markdown("""
    **Limitations**:
    - The PoC uses public modeled/satellite-derived data (ERA5/NASA POWER) rather than actual plant sensor data.
    
    **Path to Production**:
    - Integrating real ground-sensor pyranometer data.
    - Exploring recurrent models or transformers for sequence data.
    - Building a real-time ingestion pipeline.
    """)

st.caption("SuryaCast - Sahasranshu Technologies Private Limited | Rodic InfraAI Innovation Challenge 2026")
