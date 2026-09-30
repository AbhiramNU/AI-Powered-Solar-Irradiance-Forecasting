import streamlit as st

st.set_page_config(
    page_title="SuryaCast | Solar Irradiance Forecasting",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Brand visual identity elements
st.markdown("""
<style>
    /* Warm palette and clean typography */
    h1, h2, h3 {
        color: #1a1a1a;
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background-color: #fcfcfc;
    }
    .brand-title {
        font-size: 3rem;
        font-weight: 700;
        color: #d97706; /* warm amber */
        margin-bottom: 0;
        padding-bottom: 0;
    }
    .tagline {
        font-size: 1.2rem;
        color: #666;
        font-style: italic;
        margin-top: 0;
        padding-top: 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="brand-title">SURYA CAST</p>', unsafe_allow_html=True)
st.markdown('<p class="tagline">"See Tomorrow\'s Sun."</p>', unsafe_allow_html=True)

st.markdown("---")

st.markdown("""
Welcome to **SuryaCast**, an AI-powered solar irradiance forecasting PoC.

Please use the sidebar to navigate the dashboard:
- **01 Forecast View**: View tomorrow's solar forecast and uncertainty bands.
- **02 Accuracy Scorecard**: Executive overview of model performance.
- **03 Location Comparison**: Generalization across 5 Indian climate zones.
- **04 Energy Estimate**: Turn sunlight predictions into energy estimates.
- **05 Data & Method**: Methodology, architecture, and assumptions.
""")
