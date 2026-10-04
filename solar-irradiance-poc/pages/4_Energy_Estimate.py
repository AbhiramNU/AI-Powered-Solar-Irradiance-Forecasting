import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_loader import load_daily, load_forecasts, load_sites

LOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.png")
st.set_page_config(page_icon=LOGO, page_title="04 Energy | SuryaCast", layout="wide")
st.logo(LOGO, size="large")
st.sidebar.caption("SuryaCast · a product of Sahasranshu Technologies")

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
daily = load_daily()

if not sites or df.empty or daily.empty:
    st.error("Data isn't available.")
    st.stop()

# Restrict to test period and daytime hours
df = df[df["split"] == "test"]
df = df[(df["hour_ist"] >= 6) & (df["hour_ist"] <= 19)]

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

# Simplified PV model on horizontal irradiance: P(kW) = GHI(W/m²) / 1000 × capacity(kWp) × performance ratio
performance_ratio = st.slider("Performance ratio (%)", min_value=60, max_value=90, value=75, key="pr") / 100
efficiency_factor = capacity_kw * performance_ratio / 1000.0

energy_p10 = day_data["ghi_p10"] * efficiency_factor
energy_p50 = day_data["ghi_p50"] * efficiency_factor
energy_p90 = day_data["ghi_p90"] * efficiency_factor

# Daily energy from calibrated daily irradiation (kWh/m² × kWp × PR); summing hourly P10/P90 would overstate the range
d = daily[(daily["site_id"] == selected_site_id) & (daily["date"] == selected_date)].iloc[0]
st.markdown("### Estimated daily energy")
c1, c2, c3 = st.columns(3)
c1.metric("P10 energy (conservative)", f"{d['p10_kwh_m2'] * capacity_kw * performance_ratio:,.1f} kWh")
c2.metric("P50 energy (expected)", f"{d['p50_kwh_m2'] * capacity_kw * performance_ratio:,.1f} kWh")
c3.metric("P90 energy (high)", f"{d['p90_kwh_m2'] * capacity_kw * performance_ratio:,.1f} kWh")

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
- **Irradiance**: global horizontal irradiance (GHI); no plane-of-array transposition, so tilted arrays will differ.
- **Performance ratio**: {performance_ratio * 100:.0f}%, bundling temperature, soiling, inverter and wiring losses.
- **Daily range**: from the calibrated daily P10/P90, not the sum of hourly P10/P90.
- This is a simplified estimate. A production version would use `pvlib` transposition and temperature models.
""")
