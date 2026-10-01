import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_loader import load_sites, load_forecasts

st.set_page_config(page_title="04 Energy | SuryaCast", layout="wide")

st.markdown("""
<style>
    .brand-title { color: #d97706; font-size: 2rem; font-weight: bold; margin-bottom: 0; }
    .subtitle { color: #666; margin-top: 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="brand-title">SURYA CAST</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Turn sunlight into an energy estimate.</div>', unsafe_allow_html=True)
st.markdown("---")

sites = load_sites()
df = load_forecasts()

if not sites or df.empty:
    st.error("Data isn't available.")
    st.stop()

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    site_options = {s["site_id"]: s["name"] for s in sites}
    selected_site_id = st.selectbox("Location", options=list(site_options.keys()), format_func=lambda x: site_options[x])

with col2:
    available_dates = sorted(df[df["site_id"] == selected_site_id]["date"].unique())
    selected_date = st.selectbox("Date", options=available_dates)

with col3:
    capacity_kw = st.number_input("System capacity (kW)", min_value=1.0, value=100.0, step=10.0)

mask = (df["site_id"] == selected_site_id) & (df["date"] == selected_date)
day_data = df[mask].sort_values("hour_ist")

if day_data.empty:
    st.warning("No data found for this selection.")
    st.stop()

# Simplified energy placeholder logic
# In the future, this will use Akshant's energy.py (pvlib)
# E_kWh = GHI * Area * Efficiency = GHI * Capacity / 1000 * performance_ratio
performance_ratio = 0.75 
efficiency_factor = capacity_kw * performance_ratio / 1000.0

energy_p10 = day_data["ghi_p10"] * efficiency_factor
energy_p50 = day_data["ghi_p50"] * efficiency_factor
energy_p90 = day_data["ghi_p90"] * efficiency_factor

total_e_p10 = energy_p10.sum()
total_e_p50 = energy_p50.sum()
total_e_p90 = energy_p90.sum()

st.markdown("### Estimated Daily Energy")
c1, c2, c3 = st.columns(3)
c1.metric("P10 Energy", f"{total_e_p10:,.1f} kWh")
c2.metric("P50 Energy", f"{total_e_p50:,.1f} kWh")
c3.metric("P90 Energy", f"{total_e_p90:,.1f} kWh")

st.markdown("### Hourly Power Generation")
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=day_data["hour_ist"], y=energy_p90,
    mode='lines', line=dict(width=0), showlegend=False,
    name="P90 Power"
))
fig.add_trace(go.Scatter(
    x=day_data["hour_ist"], y=energy_p10,
    mode='lines', line=dict(width=0), fillcolor='rgba(217, 119, 6, 0.2)',
    fill='tonexty', name="P10-P90 Range"
))
fig.add_trace(go.Scatter(
    x=day_data["hour_ist"], y=energy_p50,
    mode='lines', line=dict(color='#d97706', width=3), name="P50 Power"
))

fig.update_layout(
    xaxis_title="Hour (IST)",
    yaxis_title="Estimated Power (kW)",
    hovermode="x unified",
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, width="stretch")

st.markdown("### Assumptions")
st.markdown(f"""
- **Fixed Tilt**: Equal to latitude
- **Orientation**: South-facing
- **Typical Losses / Performance Ratio**: {performance_ratio*100}%
- Note: This is a placeholder calculation. The production version will use `pvlib` calculations from `energy.py`.
""")
