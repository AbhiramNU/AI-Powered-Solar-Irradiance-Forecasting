import os
import streamlit as st

LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")
st.set_page_config(
    page_title="SuryaCast | Solar Irradiance Forecasting",
    page_icon=LOGO,
    layout="wide",
    initial_sidebar_state="expanded",
)
st.logo(LOGO, size="large")
st.sidebar.caption("SuryaCast · a product of Sahasranshu Technologies")

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
    .maker {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        background: #fff7ed;
        color: #9a3412;
        font-size: 0.85rem;
        font-weight: 600;
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
st.markdown('<span class="maker">A product of Sahasranshu Technologies</span>', unsafe_allow_html=True)

st.markdown("---")

st.markdown("""
Welcome to **SuryaCast**, a solar irradiance forecasting product by **Sahasranshu Technologies**.

Please use the sidebar to navigate the dashboard:
- **01 Forecast View**: View tomorrow's solar forecast and uncertainty bands.
- **02 Accuracy Scorecard**: Executive overview of model performance.
- **03 Location Comparison**: Generalization across 5 Indian climate zones.
- **04 Energy Estimate**: Turn sunlight predictions into energy estimates.
- **05 Data & Method**: Methodology, architecture, and assumptions.
""")
