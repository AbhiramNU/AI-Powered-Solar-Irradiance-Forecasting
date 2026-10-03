import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_loader import load_metrics, signed

LOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.png")
st.set_page_config(page_icon=LOGO, page_title="02 Accuracy | SuryaCast", layout="wide")
st.logo(LOGO, size="large")
st.sidebar.caption("SuryaCast · a product of Sahasranshu Technologies")

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
    st.stop()

overall = metrics["overall"]
ml_p50, raw_nwp, pers = overall["ml_model_p50"], overall["raw_nwp"], overall["persistence"]
coverage = overall["p10_p90_coverage"]
ci = overall["skill_interval"]["vs_raw_nwp"]
period = metrics["test_period"]

st.markdown(f"### Test period {period['start']} → {period['end']}, daylight hours, scored against ERA5")
verdict = "lower" if ml_p50["mae"] < raw_nwp["mae"] else "higher"
st.markdown(
    f"The model's mean absolute error is **{ml_p50['mae']:.1f} W/m²**, {verdict} than the raw weather forecast "
    f"({raw_nwp['mae']:.1f} W/m²) it starts from. Skill vs the weather forecast is **{signed(ml_p50['skill'])}%** "
    f"(95% interval {signed(ci['low'])}% to {signed(ci['high'])}%)."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("ML P50 MAE", f"{ml_p50['mae']:.1f} W/m²", f"RMSE {ml_p50['rmse']:.1f}", delta_color="off")
c2.metric("Skill vs raw NWP", f"{signed(ml_p50['skill'])}%", f"{signed(ci['low'])} to {signed(ci['high'])}%", delta_color="off")
c3.metric("P10–P90 coverage", f"{coverage:.1f}%", "target 75–85% of daylight hours", delta_color="off")
c4.metric("Quantile crossings", f"{overall['quantile_crossings']}")

ind = metrics.get("independent_check")
if ind:
    st.markdown(f"### Independent check: {ind['reference']}")
    better = ind["ml_model_p50"]["mae"] < ind["raw_nwp"]["mae"]
    msg = (f"Against NASA POWER, which neither the model nor the weather forecast was fitted to, the model's MAE is "
           f"{ind['ml_model_p50']['mae']:.1f} W/m² vs {ind['raw_nwp']['mae']:.1f} W/m² for the raw weather forecast "
           f"(ERA5 itself scores {ind['era5']['mae']:.1f}).")
    if better:
        st.success(msg + " The improvement carries over to an independent reference.")
    else:
        st.warning(msg + " The model's gain against ERA5 does not carry over: it mostly learns ERA5's systematic "
                   "differences from the weather forecast rather than predicting sunlight better.")

st.markdown("### Model vs baselines")
comp_df = pd.DataFrame([
    {"Model": "SuryaCast ML (P50)", "MAE (W/m²)": ml_p50["mae"], "RMSE (W/m²)": ml_p50["rmse"], "nRMSE (%)": ml_p50["nrmse"], "Bias (W/m²)": ml_p50["bias"], "Skill": f"{signed(ml_p50['skill'])}% vs NWP"},
    {"Model": "Raw weather forecast (ECMWF IFS)", "MAE (W/m²)": raw_nwp["mae"], "RMSE (W/m²)": raw_nwp["rmse"], "nRMSE (%)": raw_nwp["nrmse"], "Bias (W/m²)": raw_nwp["bias"], "Skill": f"{signed(raw_nwp['skill'])}% vs persistence"},
    {"Model": "Persistence (idealised*)", "MAE (W/m²)": pers["mae"], "RMSE (W/m²)": pers["rmse"], "nRMSE (%)": pers["nrmse"], "Bias (W/m²)": pers["bias"], "Skill": "Reference"},
])
st.dataframe(comp_df, hide_index=True, width="stretch")
st.caption("*Persistence uses yesterday's ERA5, which is published days later, so no real forecast could use it. "
           f"All-hours MAE for comparison with earlier reports: ML {metrics['all_hours']['ml_model_p50']['mae']:.1f}, "
           f"NWP {metrics['all_hours']['raw_nwp']['mae']:.1f} W/m².")

fig = go.Figure([
    go.Bar(name="MAE", x=comp_df["Model"], y=comp_df["MAE (W/m²)"], marker_color="#d97706"),
    go.Bar(name="RMSE", x=comp_df["Model"], y=comp_df["RMSE (W/m²)"], marker_color="#1f77b4"),
])
fig.update_layout(barmode="group", template="plotly_white", yaxis_title="Error (W/m²)")
st.plotly_chart(fig, width="stretch")

st.markdown("### Monthly performance")
months = sorted(metrics["by_month"])
fig_m = go.Figure()
for key, label, color in (("ml_model_p50", "SuryaCast ML (P50)", "#d97706"), ("raw_nwp", "Raw weather forecast", "#7f7f7f"), ("persistence", "Persistence", "#1f77b4")):
    fig_m.add_trace(go.Scatter(x=months, y=[metrics["by_month"][m]["overall"][key] for m in months], mode="lines+markers", name=label, line=dict(color=color)))
fig_m.update_layout(template="plotly_white", yaxis_title="Daylight MAE (W/m²)")
st.plotly_chart(fig_m, width="stretch")

st.markdown("### Uncertainty calibration (target 75–85% of daylight hours)")
st.progress(min(1.0, coverage / 100.0))
st.caption(f"P10–P90 band coverage: **{coverage:.2f}%**. Daily totals: **{metrics['daily']['p10_p90_coverage']:.2f}%** "
           f"of {metrics['daily']['days']} site-days.")

conf = metrics.get("by_confidence", {})
if conf:
    st.markdown("### Does the confidence label mean something?")
    st.dataframe(pd.DataFrame([{"Confidence": k, "Site-days": v["site_days"], "Daylight MAE (W/m²)": v["mae"], "Coverage (%)": v["coverage"]}
                               for k, v in conf.items()]), hide_index=True, width="stretch")
