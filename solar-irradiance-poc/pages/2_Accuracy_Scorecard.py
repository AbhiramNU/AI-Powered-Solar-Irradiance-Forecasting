import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_loader import load_metrics

st.set_page_config(page_title="02 Accuracy | SuryaCast", layout="wide")

st.markdown("""
<style>
    .brand-title { color: #d97706; font-size: 2rem; font-weight: bold; margin-bottom: 0; }
    .subtitle { color: #666; margin-top: 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="brand-title">SURYA CAST</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">How accurate is SuryaCast?</div>', unsafe_allow_html=True)
st.markdown("---")

st.info("DEMO / SAMPLE DATA — NOT FINAL MODEL OUTPUT")

metrics = load_metrics()

if not metrics:
    st.error("Metrics data isn't available.")
    st.stop()

overall = metrics.get("overall", {})
skill_nwp = overall.get("skill_vs_raw_nwp", 0)

st.markdown(f"### Model performance across the unseen 2026 test period.")
st.markdown(f"**Across five sites in 2026, the model's error was {skill_nwp}% lower than the raw weather forecast.**")

st.markdown("### Performance Overview")
c1, c2, c3, c4 = st.columns(4)
c1.metric("MAE", f"{overall.get('MAE', 0):.1f} W/m²")
c2.metric("RMSE", f"{overall.get('RMSE', 0):.1f} W/m²")
c3.metric("Skill vs NWP", f"{overall.get('skill_vs_raw_nwp', 0):.1f}%")
c4.metric("P10-P90 Coverage", f"{overall.get('P10_P90_coverage', 0):.1f}%")

st.markdown("### Monthly Behaviour (RMSE)")
monthly = metrics.get("by_month", {})
if monthly:
    months = list(monthly.keys())
    rmses = [m["RMSE"] for m in monthly.values()]
    fig = go.Figure([go.Bar(x=months, y=rmses, marker_color='#d97706')])
    fig.update_layout(template="plotly_white", xaxis_title="Month", yaxis_title="RMSE (W/m²)")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("### Uncertainty Calibration")
st.markdown("The P10-P90 coverage target is roughly 80%.")
coverage = overall.get("P10_P90_coverage", 0)
st.progress(coverage / 100.0)
st.caption(f"Actual Coverage: {coverage:.1f}%")
