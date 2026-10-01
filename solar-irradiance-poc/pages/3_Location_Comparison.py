import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_loader import load_sites, load_metrics

st.set_page_config(page_title="03 Locations | SuryaCast", layout="wide")

st.markdown("""
<style>
    .brand-title { color: #d97706; font-size: 2rem; font-weight: bold; margin-bottom: 0; }
    .subtitle { color: #666; margin-top: 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="brand-title">SURYA CAST</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Does the model generalise across India?</div>', unsafe_allow_html=True)
st.markdown("---")

metrics = load_metrics()
sites = load_sites()

if not sites or not metrics:
    st.error("Data isn't available.")
    st.stop()

st.markdown("### Location Comparison (2026 Test Period)")

by_site = metrics.get("by_site", {})

data = []
for s in sites:
    site_id = s["site_id"]
    site_metrics = by_site.get(site_id, {})
    ml_m = site_metrics.get("ml_model_p50", {})
    data.append({
        "Site": str(s["name"]),
        "Climate Zone": str(s["climate_zone"]),
        "Latitude": float(s["latitude"]),
        "Longitude": float(s["longitude"]),
        "MAE (W/m²)": float(ml_m.get("mae", 0)),
        "RMSE (W/m²)": float(ml_m.get("rmse", 0)),
        "Skill vs NWP (%)": float(ml_m.get("skill", 0)),
        "Coverage (%)": float(site_metrics.get("coverage", 0))
    })

df = pd.DataFrame(data)

col1, col2 = st.columns([1, 1])

with col1:
    st.dataframe(df.drop(columns=["Latitude", "Longitude"]), width="stretch", hide_index=True)

with col2:
    try:
        fig = px.scatter_mapbox(df, lat="Latitude", lon="Longitude", hover_name="Site", 
                                hover_data=["Climate Zone", "MAE (W/m²)", "Coverage (%)"],
                                color="MAE (W/m²)", size_max=15, zoom=4, height=400,
                                mapbox_style="carto-positron")
        st.plotly_chart(fig, width="stretch")
    except Exception as e:
        st.caption("Map visualization unavailable.")
st.markdown("### Monthly Error Heatmap")
st.info("Site × Month Error Matrix: Not available in current metrics schema.")

st.markdown("---")
st.markdown("*To view detailed hourly forecasts for any of these sites, please navigate to the **01 Forecast View** page from the sidebar.*")
