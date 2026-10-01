import json
import pandas as pd
import streamlit as st
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIMARY_DATA_DIR = os.path.join(BASE_DIR, "data")
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "data", "sample")

def get_data_dir():
    if os.path.exists(os.path.join(PRIMARY_DATA_DIR, "forecasts.parquet")):
        return PRIMARY_DATA_DIR
    return SAMPLE_DATA_DIR

@st.cache_data
def load_sites():
    data_dir = get_data_dir()
    try:
        with open(os.path.join(data_dir, "sites.json"), "r") as f:
            data = json.load(f)
            
            # Validation - support both list format [...] and dict format {"sites": [...]}
            if isinstance(data, list):
                sites = data
            elif isinstance(data, dict):
                sites = data.get("sites", [])
            else:
                sites = []

            for site in sites:
                if not all(k in site for k in ["site_id", "name", "latitude", "longitude", "climate_zone"]):
                    st.error("Validation Error: sites.json missing required fields.")
                    return []
            return sites
    except Exception as e:
        st.error(f"Error loading sites.json: {e}")
        return []

@st.cache_data
def load_forecasts():
    data_dir = get_data_dir()
    try:
        df = pd.read_parquet(os.path.join(data_dir, "forecasts.parquet"))
        
        # Validation
        required_cols = ["site_id", "date", "hour_ist", "ghi_actual", "ghi_p10", "ghi_p50", 
                         "ghi_p90", "ghi_nwp", "ghi_persistence", "ghi_clearsky", "confidence", "split"]
        
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            st.error(f"Validation Error: forecasts.parquet missing columns: {missing_cols}")
            return pd.DataFrame()
            
        # P10 <= P50 <= P90 validation (ignoring NaNs)
        invalid_p = df[~((df['ghi_p10'] <= df['ghi_p50']) & (df['ghi_p50'] <= df['ghi_p90'])) & df['ghi_p50'].notnull()]
        if not invalid_p.empty:
            st.warning("Validation Warning: Some rows violate P10 <= P50 <= P90.")
            
        return df
    except Exception as e:
        st.error(f"Error loading forecasts.parquet: {e}")
        return pd.DataFrame()

@st.cache_data
def load_metrics():
    data_dir = get_data_dir()
    try:
        with open(os.path.join(data_dir, "metrics.json"), "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        st.error(f"Error loading metrics.json: {e}")
        return {}
