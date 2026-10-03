"""End-to-end pipeline on synthetic data: run, contract, determinism, model persistence, publish."""

import json

import numpy as np
import pandas as pd
import pytest

from src.config import load_run_config
from src.contract import validate_daily, validate_forecasts, validate_metrics
from src.data.sites import load_and_validate_sites
from src.dataset import build_dataset
from src.features import build_features
from src.model import QuantileForecaster
from src.pipeline import run
from src.publish import export_frontend, load_contract, publish_run
from tests.synthetic import make_run_config, write_raw, write_sites


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("e2e")
    write_raw(tmp / "raw")
    cfg = load_run_config(make_run_config(tmp))
    sites = load_and_validate_sites(write_sites(tmp))
    run_dir = run(cfg, sites, "test-run", raw_dir=tmp / "raw", runs_dir=tmp / "runs")
    return {"run_dir": run_dir, "cfg": cfg, "sites": sites, "raw": tmp / "raw", "runs": tmp / "runs"}


@pytest.fixture(scope="module")
def run_dir(env):
    return env["run_dir"]


def test_run_outputs_satisfy_contract(run_dir):
    hourly = pd.read_parquet(run_dir / "forecasts.parquet")
    daily = pd.read_parquet(run_dir / "daily_forecasts.parquet")
    metrics = json.loads((run_dir / "metrics.json").read_text())
    validate_forecasts(hourly)
    validate_daily(daily)
    validate_metrics(metrics, ["AAA", "BBB"])
    assert metrics["test_period"]["start"].startswith("2026")
    assert metrics["overall"]["quantile_crossings"] == 0


def test_night_is_zero_and_quantiles_ordered(run_dir):
    f = pd.read_parquet(run_dir / "forecasts.parquet")
    night = f[~f["is_daylight"]]
    assert (night[["ghi_p10", "ghi_p50", "ghi_p90"]] == 0).all().all()
    assert ((f.ghi_p10 <= f.ghi_p50) & (f.ghi_p50 <= f.ghi_p90)).all()


def test_daily_band_is_narrower_than_summed_hourly_quantiles(run_dir):
    f = pd.read_parquet(run_dir / "forecasts.parquet")
    d = pd.read_parquet(run_dir / "daily_forecasts.parquet").set_index(["site_id", "date"])
    summed = f.groupby(["site_id", "date"])[["ghi_p10", "ghi_p90"]].sum() / 1000
    width_daily = (d["p90_kwh_m2"] - d["p10_kwh_m2"])
    width_summed = (summed["ghi_p90"] - summed["ghi_p10"]).reindex(width_daily.index)
    assert (width_daily <= width_summed + 1e-9).all()


def test_saved_model_reproduces_predictions(env):
    run_dir, cfg = env["run_dir"], env["cfg"]
    model = QuantileForecaster.load(run_dir / "model")
    assert set(model.boosters) == {"p10", "p50", "p90"}
    assert not list(run_dir.rglob("*.pkl"))
    data, _ = build_dataset(env["sites"], cfg, env["raw"])
    frame, _ = build_features(data, cfg)
    pred = frame[["site_id", "date", "hour_ist"]].join(model.predict(frame))
    published = pd.read_parquet(run_dir / "forecasts.parquet")
    merged = published.merge(pred, on=["site_id", "date", "hour_ist"], suffixes=("", "_reloaded"))
    assert len(merged) == len(published)
    np.testing.assert_allclose(merged["ghi_p50"], merged["ghi_p50_reloaded"], atol=1e-6)
    assert (merged["confidence"] == merged["confidence_reloaded"]).all()


def test_rerun_is_deterministic(env):
    again = run(env["cfg"], env["sites"], "test-run-2", raw_dir=env["raw"], runs_dir=env["runs"])
    a = pd.read_parquet(env["run_dir"] / "forecasts.parquet")
    b = pd.read_parquet(again / "forecasts.parquet")
    pd.testing.assert_frame_equal(a, b)


def test_run_records_provenance(run_dir):
    env = json.loads((run_dir / "environment.json").read_text())
    assert env["packages"]["lightgbm"] and env["python"]
    cfg = json.loads((run_dir / "config.json").read_text())
    assert cfg["run"]["splits"]["test"] == [2026]
    report = (run_dir / "reports" / "data_quality.md").read_text()
    assert "Quality gates" in report and "PASS" in report


def test_publish_validates_and_exports_frontend(run_dir, tmp_path):
    publish_run(run_dir, dashboard_dir=tmp_path / "dash", frontend_dir=tmp_path / "fe", reports_dir=tmp_path / "rep")
    c = load_contract(tmp_path / "dash")
    assert c["metrics"]["run_id"] == "test-run"
    site = json.loads((tmp_path / "fe" / "forecasts" / "AAA.json").read_text())
    day = next(iter(site["days"].values()))
    assert set(day["daily"]) == {"actual", "p10", "p50", "p90", "nwp"}
    assert len(day["p50"]) == len(site["hours"])
    assert (tmp_path / "rep" / "PUBLISHED_RUN").read_text().strip() == "test-run"


def test_publish_refuses_invalid_outputs(run_dir, tmp_path):
    bad = tmp_path / "bad"
    bad.mkdir()
    for f in ("sites.json", "daily_forecasts.parquet", "metrics.json"):
        (bad / f).write_bytes((run_dir / f).read_bytes())
    f = pd.read_parquet(run_dir / "forecasts.parquet")
    f.loc[f.index[0], "ghi_p10"] = 999.0
    f.to_parquet(bad / "forecasts.parquet")
    with pytest.raises(ValueError):
        export_frontend(bad, tmp_path / "fe2")
