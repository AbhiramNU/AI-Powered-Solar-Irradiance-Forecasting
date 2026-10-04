import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_loader import load_daily, load_forecasts, load_sites

LOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.png")
st.set_page_config(page_icon=LOGO, page_title="01 Forecast | SuryaCast", layout="wide")
st.logo(LOGO, size="large")
st.sidebar.caption("SuryaCast · a product of Sahasranshu Technologies")

st.markdown("""
<style>
    h1, h2, h3 { color: #1a1a1a; font-family: 'Inter', sans-serif; }
    .stAlert { background-color: #fff3cd; color: #856404; }
    .brand-title { color: #d97706; font-size: 2rem; font-weight: bold; margin-bottom: 0; }
    .subtitle { color: #666; margin-top: 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="brand-title">SURYA CAST</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Tomorrow\'s Solar Forecast</div>', unsafe_allow_html=True)
st.markdown("---")

st.success("Test period (2026) — Model evaluation on unseen data.")

sites = load_sites()
df = load_forecasts()
daily = load_daily()

if not sites or df.empty or daily.empty:
    st.error("Forecast data isn't available for this selection yet.")
    st.stop()

# Restrict to test period and daytime hours
df = df[df["split"] == "test"]
df = df[(df["hour_ist"] >= 6) & (df["hour_ist"] <= 19)]

# Layout
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    site_options = {s["site_id"]: s["name"] for s in sites}
    selected_site_id = st.selectbox("Location", options=list(site_options.keys()), format_func=lambda x: site_options[x])

with col2:
    available_dates = sorted(df[df["site_id"] == selected_site_id]["date"].unique())
    selected_date = st.selectbox("Date", options=available_dates)

with col3:
    st.write("")
    st.write("")
    if st.button("☁ Explore a cloudy day"):
        site_data = df[df["site_id"] == selected_site_id]
        if not site_data.empty:
            # A cloudy day has a large gap between clearsky and actual GHI
            daily_diff = site_data.groupby("date").apply(lambda x: (x["ghi_clearsky"] - x["ghi_actual"]).sum(), include_groups=False)
            cloudy_date = daily_diff.idxmax()
            selected_date = cloudy_date
            st.session_state["cloudy_btn"] = True
            st.rerun()

if st.session_state.get("cloudy_btn", False):
    st.caption("Cloud-driven variability makes solar forecasting harder.")
    st.session_state["cloudy_btn"] = False

# Filter data
mask = (df["site_id"] == selected_site_id) & (df["date"] == selected_date)
day_data = df[mask].sort_values("hour_ist")

if day_data.empty:
    st.warning("No data found for this selection.")
    st.stop()

# Daily summary: daily P10/P90 are calibrated for daily totals (summing hourly quantiles overstates the range)
d = daily[(daily["site_id"] == selected_site_id) & (daily["date"] == selected_date)].iloc[0]
actual_total = d["actual_kwh_m2"]
has_actual = pd.notna(actual_total) and actual_total > 0

st.markdown("### Daily irradiation")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("P50 forecast (expected)", f"{d['p50_kwh_m2']:.2f} kWh/m²")
c2.metric("P10 (conservative)", f"{d['p10_kwh_m2']:.2f} kWh/m²")
c3.metric("P90 (high generation)", f"{d['p90_kwh_m2']:.2f} kWh/m²")
if has_actual:
    error_pct = abs(d["p50_kwh_m2"] - actual_total) / actual_total * 100
    in_band = d["p10_kwh_m2"] <= actual_total <= d["p90_kwh_m2"]
    c4.metric("Actual (ERA5)", f"{actual_total:.2f} kWh/m²",
              f"{error_pct:.1f}% error · {'inside' if in_band else 'outside'} P10–P90", delta_color="off")
else:
    c4.metric("Actual (ERA5)", "n/a")
c5.metric("Confidence", d["confidence"])

st.markdown("### Hourly Forecast")
st.caption("Shaded area is the P10–P90 range. Each point is the mean over the hour centred on the label (12:00 = 11:30–12:30 IST).")

fig = go.Figure()

# P90
fig.add_trace(go.Scatter(
    x=day_data["hour_ist"], y=day_data["ghi_p90"],
    mode='lines', line=dict(width=0), showlegend=False,
    name="P90"
))

# P10
fig.add_trace(go.Scatter(
    x=day_data["hour_ist"], y=day_data["ghi_p10"],
    mode='lines', line=dict(width=0), fillcolor='rgba(217, 119, 6, 0.2)',
    fill='tonexty', name="P10-P90 Uncertainty Band"
))

# P50
fig.add_trace(go.Scatter(
    x=day_data["hour_ist"], y=day_data["ghi_p50"],
    mode='lines', line=dict(color='#d97706', width=3), name="P50 Forecast"
))

# Actual
fig.add_trace(go.Scatter(
    x=day_data["hour_ist"], y=day_data["ghi_actual"],
    mode='markers+lines', marker=dict(color='#1f77b4', size=6), line=dict(width=1, dash='dot'), name="Actual GHI (ERA5)"
))

# NWP
fig.add_trace(go.Scatter(
    x=day_data["hour_ist"], y=day_data["ghi_nwp"],
    mode='lines', line=dict(color='#7f7f7f', width=2, dash='dash'), name="Raw weather forecast (ECMWF IFS)"
))

fig.update_layout(
    xaxis_title="Hour (IST)",
    yaxis_title="GHI (W/m²)",
    hovermode="x unified",
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, width="stretch")
