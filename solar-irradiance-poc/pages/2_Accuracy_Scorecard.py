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

metrics = load_metrics()

if not metrics:
    st.error("Metrics data isn't available.")
    st.stop()

overall = metrics.get("overall", {})
ml_p50 = overall.get("ml_model_p50", {})
raw_nwp = overall.get("raw_nwp", {})
pers = overall.get("persistence", {})
coverage = overall.get("p10_p90_coverage", 0.0)

st.markdown(f"### Model performance across the unseen 2026 test period.")
st.markdown(f"**Across five Indian sites in 2026, the LightGBM ML model achieved a Mean Absolute Error of {ml_p50.get('mae', 0):.2f} W/m², outperforming both the raw weather forecast ({raw_nwp.get('mae', 0):.2f} W/m²) and the persistence baseline ({pers.get('mae', 0):.2f} W/m²).**")

st.markdown("### Performance Overview (2026 Test Set)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("ML Model P50 MAE", f"{ml_p50.get('mae', 0):.2f} W/m²")
c2.metric("ML Model P50 RMSE", f"{ml_p50.get('rmse', 0):.2f} W/m²")
c3.metric("Skill vs Raw NWP", f"{ml_p50.get('skill', 0):.2f}%")
c4.metric("P10-P90 Coverage", f"{coverage:.1f}%")

st.markdown("### Model vs Baselines Comparison")
comp_df = pd.DataFrame([
    {"Model": "LightGBM Quantile (P50)", "MAE (W/m²)": ml_p50.get("mae", 0), "RMSE (W/m²)": ml_p50.get("rmse", 0), "nRMSE (%)": ml_p50.get("nrmse", 0)},
    {"Model": "Raw Weather Forecast (NWP)", "MAE (W/m²)": raw_nwp.get("mae", 0), "RMSE (W/m²)": raw_nwp.get("rmse", 0), "nRMSE (%)": raw_nwp.get("nrmse", 0)},
    {"Model": "Persistence Baseline", "MAE (W/m²)": pers.get("mae", 0), "RMSE (W/m²)": pers.get("rmse", 0), "nRMSE (%)": pers.get("nrmse", 0)},
])

fig = go.Figure([
    go.Bar(name="MAE", x=comp_df["Model"], y=comp_df["MAE (W/m²)"], marker_color="#d97706"),
    go.Bar(name="RMSE", x=comp_df["Model"], y=comp_df["RMSE (W/m²)"], marker_color="#1f77b4"),
])
fig.update_layout(barmode="group", template="plotly_white", yaxis_title="Error (W/m²)")
st.plotly_chart(fig, use_container_width=True)

st.markdown("### Uncertainty Calibration Target (75% – 85%)")
st.progress(min(1.0, coverage / 100.0))
st.caption(f"Measured Test Set P10–P90 Band Coverage: **{coverage:.2f}%** (Target: 75% – 85%)")
