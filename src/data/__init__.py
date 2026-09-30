"""
Data ingestion and validation modules for Solar Irradiance Prediction PoC.
"""

from src.data.open_meteo_previous_runs import fetch_previous_run
from src.data.open_meteo_era5 import fetch_era5_ghi
from src.data.nasa_power import fetch_nasa_power_ghi
from src.data.sites import load_and_validate_sites
from src.data.validation import validate_api_dataframe

__all__ = [
    "fetch_previous_run",
    "fetch_era5_ghi",
    "fetch_nasa_power_ghi",
    "load_and_validate_sites",
    "validate_api_dataframe",
]
