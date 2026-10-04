import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_loader import load_sites, load_metrics, signed

LOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.png")
st.set_page_config(page_icon=LOGO, page_title="03 Locations | SuryaCast", layout="wide")
st.logo(LOGO, size="large")
st.sidebar.caption("SuryaCast · a product of Sahasranshu Technologies")

st.markdown("""
<style>
    .brand-title { color: #d97706; font-size: 2rem; font-weight: bold; margin-bottom: 0; }
    .subtitle { color: #666; margin-top: 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="brand-title">SURYA CAST</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">How does performance vary across sites?</div>', unsafe_allow_html=True)
st.markdown("---")

metrics = load_metrics()
sites = load_sites()

if not sites or not metrics:
    st.stop()

st.markdown("### Location comparison (test period, daylight hours, vs ERA5)")

rows = []
for s in sites:
    m = metrics["by_site"][s["site_id"]]
    ci = m["skill_interval"]["vs_raw_nwp"]
    rows.append({
        "Site": s["name"],
        "Climate Zone": s["climate_zone"],
        "Latitude": float(s["latitude"]),
        "Longitude": float(s["longitude"]),
        "MAE (W/m²)": m["ml_model_p50"]["mae"],
        "Raw NWP MAE (W/m²)": m["raw_nwp"]["mae"],
        "Skill vs NWP (%)": signed(m["ml_model_p50"]["skill"]),
        "Skill 95% interval": f"{signed(ci['low'])} to {signed(ci['high'])}",
        "Coverage (%)": m["coverage"],
    })
df = pd.DataFrame(rows)

col1, col2 = st.columns([1, 1])
with col1:
    st.dataframe(df.drop(columns=["Latitude", "Longitude"]), width="stretch", hide_index=True)
with col2:
    fig = px.scatter_map(df, lat="Latitude", lon="Longitude", hover_name="Site",
                         hover_data=["Climate Zone", "MAE (W/m²)", "Coverage (%)"],
                         color="MAE (W/m²)", zoom=4, height=400, map_style="carto-positron")
    st.plotly_chart(fig, width="stretch")

st.markdown("### Monthly error by site")
months = sorted(metrics["by_month"])
heat = pd.DataFrame({m: {s["name"]: metrics["by_month"][m]["by_site"].get(s["site_id"]) for s in sites} for m in months})
st.plotly_chart(px.imshow(heat, color_continuous_scale="Oranges", aspect="auto", labels=dict(color="Daylight MAE (W/m²)"), text_auto=".0f"),
                width="stretch")

st.markdown("---")
st.markdown("*To view hourly forecasts for any of these sites, open **01 Forecast View** from the sidebar.*")
