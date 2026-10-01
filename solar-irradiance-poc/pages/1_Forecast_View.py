import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_loader import load_sites, load_forecasts

st.set_page_config(page_title="01 Forecast | SuryaCast", layout="wide")

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

if not sites or df.empty:
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

# Summaries
p10_sum = day_data["ghi_p10"].sum()
p50_sum = day_data["ghi_p50"].sum()
p90_sum = day_data["ghi_p90"].sum()
actual_sum = day_data["ghi_actual"].sum()
error_pct = abs(p50_sum - actual_sum) / actual_sum * 100 if actual_sum > 0 else 0
confidence = day_data["confidence"].iloc[0] if "confidence" in day_data.columns else "Medium"

st.markdown("### Daily Summary")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("P50 Forecast (Expected)", f"{p50_sum:,.0f} W/m²")
c2.metric("P10 (Conservative)", f"{p10_sum:,.0f} W/m²")
c3.metric("P90 (High-generation)", f"{p90_sum:,.0f} W/m²")
c4.metric("Actual", f"{actual_sum:,.0f} W/m²", f"{error_pct:.1f}% Error", delta_color="inverse")
c5.metric("Confidence", confidence)

st.markdown("### Hourly Forecast")
st.caption("Shaded area represents the model's prediction range.")

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
    mode='markers+lines', marker=dict(color='#1f77b4', size=6), line=dict(width=1, dash='dot'), name="Actual GHI"
))

# NWP
fig.add_trace(go.Scatter(
    x=day_data["hour_ist"], y=day_data["ghi_nwp"],
    mode='lines', line=dict(color='#7f7f7f', width=2, dash='dash'), name="Raw Weather Forecast"
))

fig.update_layout(
    xaxis_title="Hour (IST)",
    yaxis_title="GHI (W/m²)",
    hovermode="x unified",
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, width="stretch")
