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

st.info("DEMO / SAMPLE DATA — NOT FINAL MODEL OUTPUT")

sites = load_sites()
metrics = load_metrics()

if not sites or not metrics:
    st.error("Data isn't available.")
    st.stop()

st.markdown("### Location Comparison")

by_site = metrics.get("by_site", {})

data = []
for s in sites:
    site_metrics = by_site.get(s["site_id"], {})
    data.append({
        "Site": s["name"],
        "Climate Zone": s["climate_zone"],
        "Latitude": s["latitude"],
        "Longitude": s["longitude"],
        "MAE (W/m²)": site_metrics.get("MAE", 0),
        "Skill vs NWP (%)": site_metrics.get("skill_vs_raw_nwp", 0),
        "P10-P90 Coverage (%)": site_metrics.get("P10_P90_coverage", 0)
    })

df = pd.DataFrame(data)

col1, col2 = st.columns([1, 1])

with col1:
    st.dataframe(df.drop(columns=["Latitude", "Longitude"]), use_container_width=True, hide_index=True)

with col2:
    try:
        fig = px.scatter_mapbox(df, lat="Latitude", lon="Longitude", hover_name="Site", 
                                hover_data=["Climate Zone", "MAE (W/m²)"],
                                color="MAE (W/m²)", size_max=15, zoom=4, height=400,
                                mapbox_style="carto-positron")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.caption("Map visualization unavailable.")

st.markdown("### Monthly Error Heatmap")
st.caption("Site x Month Error Matrix will be rendered here once monthly data per site is available.")
