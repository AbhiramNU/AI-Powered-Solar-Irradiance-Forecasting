"""
Synthetic raw files for offline tests (never used outside the test suite).

Truth is clear-sky GHI times a day-level cloud factor; each NWP model sees that factor
with its own noise, so the forecast carries real but imperfect information.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.physics import hourly_solar_geometry

TEST_SITES: List[Dict[str, Any]] = [
    {"site_id": "AAA", "name": "Alpha", "latitude": 26.0, "longitude": 73.0, "altitude_m": 230, "climate_zone": "Arid"},
    {"site_id": "BBB", "name": "Beta", "latitude": 13.0, "longitude": 80.3, "altitude_m": 6, "climate_zone": "Tropical"},
]
MODELS = {"ec": "model_a", "gfs": "model_b"}


def make_run_config(tmp_path: Path, start: str = "2024-11-01", end: str = "2026-01-20") -> Path:
    cfg = json.loads((Path(__file__).resolve().parents[1] / "config" / "run.json").read_text())
    cfg.update({"run_name": "test", "start_date": start, "end_date": end})
    cfg["nwp"]["models"] = MODELS
    cfg["nwp"]["optional_variables"] = ["cloud_cover", "diffuse_radiation"]
    cfg["model"]["params"].update({"n_estimators": 60, "learning_rate": 0.1, "min_child_samples": 20})
    cfg["model"]["early_stopping_rounds"] = 10
    cfg["evaluation"]["bootstrap_samples"] = 50
    path = tmp_path / "run.json"
    path.write_text(json.dumps(cfg))
    return path


def write_raw(raw_dir: Path, start: str = "2024-11-01", end: str = "2026-01-20", seed: int = 0,
              nwp_nan_rows: int = 0) -> None:
    rng = np.random.default_rng(seed)
    ends = pd.date_range(f"{start} 00:00", f"{end} 23:00", freq="h", tz="UTC")
    days = ends.floor("D")
    unique_days = days.unique()
    for site in TEST_SITES:
        geo = hourly_solar_geometry(ends, site, substeps=4)
        cs = geo["ghi_clearsky"].to_numpy()
        cloud = pd.Series(rng.beta(2, 1.2, len(unique_days)), index=unique_days).reindex(days).to_numpy()
        truth = cs * (0.25 + 0.75 * cloud) * rng.normal(1, 0.05, len(ends)).clip(0.7, 1.3)
        (raw_dir / "era5").mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"time": ends, "shortwave_radiation": truth.round(1)}).to_parquet(raw_dir / "era5" / f"{site['site_id']}.parquet")
        (raw_dir / "nwp").mkdir(parents=True, exist_ok=True)
        for i, model in enumerate(MODELS.values()):
            seen = np.clip(cloud + rng.normal(0, 0.15 + 0.1 * i, len(ends)), 0, 1)
            ghi = cs * (0.25 + 0.75 * seen) + 20 * i
            df = pd.DataFrame({
                "time": ends,
                "shortwave_radiation": ghi.round(1),
                "cloud_cover": ((1 - seen) * 100).round(0),
                "diffuse_radiation": (ghi * (0.2 + 0.6 * (1 - seen))).round(1),
            })
            if nwp_nan_rows:
                df.loc[df.index[:nwp_nan_rows], "shortwave_radiation"] = np.nan
            df.to_parquet(raw_dir / "nwp" / f"{site['site_id']}_{model}.parquet")
        nasa = pd.DataFrame({"time": ends - pd.Timedelta(hours=1), "ALLSKY_SFC_SW_DWN": (truth * rng.normal(1, 0.08, len(ends))).round(1)})
        (raw_dir / "nasa_power").mkdir(parents=True, exist_ok=True)
        nasa.to_parquet(raw_dir / "nasa_power" / f"{site['site_id']}.parquet")
    (raw_dir / "manifest.json").write_text(json.dumps({"files": []}))


def write_sites(tmp_path: Path) -> Path:
    path = tmp_path / "sites.json"
    path.write_text(json.dumps(TEST_SITES))
    return path
