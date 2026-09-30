"""
Central configuration and constants for Solar Irradiance Prediction PoC.
"""

from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SAMPLES_DATA_DIR = DATA_DIR / "samples"
REPORTS_DIR = ROOT_DIR / "reports"

SITES_CONFIG_FILE = CONFIG_DIR / "sites.json"
DATA_AVAILABILITY_REPORT = REPORTS_DIR / "data_availability.md"
SOLAR6_RESULTS_JSON = REPORTS_DIR / "solar6_results.json"

# Timezone
DEFAULT_TIMEZONE = "Asia/Kolkata"

# Model Input Variables (Day-Ahead / Previous Runs 1-Day Lead Time)
REQUIRED_FORECAST_VARIABLES = [
    "shortwave_radiation_previous_day1",
    "cloud_cover_low_previous_day1",
    "cloud_cover_mid_previous_day1",
    "cloud_cover_high_previous_day1",
    "temperature_2m_previous_day1",
    "relative_humidity_2m_previous_day1",
]

# Variable Mappings and Display Names
VARIABLE_NAME_MAP = {
    "shortwave_radiation_previous_day1": "Forecast GHI",
    "cloud_cover_low_previous_day1": "Low Cloud Cover",
    "cloud_cover_mid_previous_day1": "Mid Cloud Cover",
    "cloud_cover_high_previous_day1": "High Cloud Cover",
    "temperature_2m_previous_day1": "Temperature",
    "relative_humidity_2m_previous_day1": "Relative Humidity",
}

# API Endpoints
OPEN_METEO_PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
OPEN_METEO_ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
