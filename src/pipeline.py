"""
SuryaCast pipeline command line.

    python -m src.pipeline ingest [--refresh] [--no-nasa]   download raw data (cached)
    python -m src.pipeline run [--run-id ID]                 dataset → features → train → evaluate → runs/<id>/
    python -m src.pipeline publish [--run-id ID]             validate a run and copy it to the dashboards
    python -m src.pipeline all [--refresh]                   ingest + run + publish
    python -m src.pipeline contract-doc                      regenerate the output contract document

Each run writes a self-describing directory: the resolved config, package versions and git
commit, SHA-256 of every raw input, the model, the contract outputs and generated reports.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.config import (
    CONTRACT_DOC,
    RAW_DATA_DIR,
    ROOT_DIR,
    RUN_CONFIG_FILE,
    RUNS_DIR,
    SITES_CONFIG_FILE,
    RunConfig,
    load_run_config,
)
from src.contract import FORECAST_COLUMNS, render_contract_markdown, validate_daily, validate_forecasts, validate_metrics, validate_sites
from src.crosscheck import align_nasa, compare_era5_nasa
from src.data.sites import load_and_validate_sites
from src.dataset import build_dataset
from src.evaluate import evaluate, independent_check
from src.features import build_features, describe_features, feature_names
from src.ingest import ingest_all, nasa_path
from src.model import daily_totals, fit_forecaster
from src.publish import publish_run
from src.reports import data_quality_report, evaluation_report

logger = logging.getLogger("suryacast")

PACKAGES = ("numpy", "pandas", "pyarrow", "pvlib", "lightgbm", "scikit-learn", "requests")


# ---------- provenance ----------

def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT_DIR, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def make_run_id() -> str:
    sha = _git("rev-parse", "--short", "HEAD") or "nogit"
    dirty = "-dirty" if _git("status", "--porcelain", "--untracked-files=no") else ""
    return f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{sha}{dirty}"


def environment_record() -> Dict[str, Any]:
    versions = {}
    for p in PACKAGES:
        try:
            versions[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            versions[p] = None
    return {"python": platform.python_version(), "platform": platform.platform(), "packages": versions,
            "git_commit": _git("rev-parse", "HEAD"), "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no"))}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def data_manifest(raw_dir: Path) -> Dict[str, Any]:
    manifest_path = raw_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"files": []}
    for entry in manifest["files"]:
        p = raw_dir.parent / entry["file"]
        entry["sha256"] = _sha256(p) if p.exists() else None
    return manifest


# ---------- stages ----------

def to_contract_forecasts(frame: pd.DataFrame) -> pd.DataFrame:
    cols = [c.name for c in FORECAST_COLUMNS]
    out = frame[cols].copy()
    out["hour_ist"] = out["hour_ist"].astype("int64")
    out["is_daylight"] = out["is_daylight"].astype(bool)
    return out.sort_values(["site_id", "date", "hour_ist"]).reset_index(drop=True)


def run(cfg: RunConfig, sites: List[Dict[str, Any]], run_id: str, raw_dir: Path = RAW_DATA_DIR,
        runs_dir: Path = RUNS_DIR) -> Path:
    run_dir = runs_dir / run_id
    (run_dir / "reports").mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(run_dir / "run.log")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    try:
        logger.info(f"Run {run_id}")
        data, qc = build_dataset(sites, cfg, raw_dir)

        crosscheck, nasa_parts = {}, []
        for site in sites:
            p = nasa_path(raw_dir, site["site_id"])
            if p.exists():
                site_frame, nasa = data[data["site_id"] == site["site_id"]], pd.read_parquet(p)
                crosscheck[site["site_id"]] = compare_era5_nasa(site_frame, nasa)
                nasa_parts.append(align_nasa(site_frame, nasa, crosscheck[site["site_id"]]["best_lag_hours"]))
            else:
                logger.warning(f"[{site['site_id']}] NASA POWER file missing; cross-check skipped")
        ghi_nasa = pd.concat(nasa_parts).reindex(data.index) if nasa_parts else pd.Series(float("nan"), index=data.index)

        frame, specs = build_features(data, cfg)
        features = feature_names(specs)
        logger.info(f"{len(features)} features: " + json.dumps(describe_features(specs)))

        forecaster = fit_forecaster(frame, features, cfg)
        forecaster.save(run_dir / "model")

        pred = forecaster.predict(frame)
        frame = frame.join(pred)
        frame["ghi_nwp"] = frame[forecaster.config.primary_ghi]
        hourly = to_contract_forecasts(frame)
        daily = daily_totals(hourly, forecaster.config.daily_band_multiplier)

        model_version = f"{cfg.run_name}@{run_id}"
        test_mask = (frame["split"] == "test").to_numpy()
        test_frame = frame.loc[test_mask, [c.name for c in FORECAST_COLUMNS]]
        independent = independent_check(test_frame, ghi_nasa.loc[test_frame.index], "NASA POWER (SYN1DEG, satellite-derived)")
        metrics = evaluate(
            hourly[hourly["split"] == "test"], daily[daily["split"] == "test"], sites,
            run_id=run_id, model_version=model_version, quantiles=cfg.quantiles,
            n_boot=cfg.bootstrap_samples, seed=cfg.bootstrap_seed, level=cfg.interval_level,
            independent=independent,
        )

        site_records = [{k: s[k] for k in ("site_id", "name", "latitude", "longitude", "altitude_m", "climate_zone")} for s in sites]
        validate_sites(site_records)
        validate_forecasts(hourly)
        validate_daily(daily)
        validate_metrics(metrics, [s["site_id"] for s in sites])

        hourly.to_parquet(run_dir / "forecasts.parquet", index=False)
        daily.to_parquet(run_dir / "daily_forecasts.parquet", index=False)
        (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
        (run_dir / "sites.json").write_text(json.dumps(site_records, indent=2))
        (run_dir / "config.json").write_text(json.dumps({"run": cfg.raw, "sites": sites}, indent=2))
        (run_dir / "environment.json").write_text(json.dumps(environment_record(), indent=2))
        manifest = data_manifest(raw_dir)
        (run_dir / "data_manifest.json").write_text(json.dumps(manifest, indent=2))
        (run_dir / "features.json").write_text(json.dumps([s.__dict__ for s in specs], indent=2))
        (run_dir / "quality.json").write_text(json.dumps({"qc": qc, "crosscheck": crosscheck}, indent=2))

        (run_dir / "reports" / "data_quality.md").write_text(data_quality_report(run_id, qc, crosscheck, manifest, cfg.raw))
        (run_dir / "reports" / "evaluation.md").write_text(evaluation_report(
            metrics, forecaster.config.selection, json.loads((run_dir / "model" / "forecaster.json").read_text()),
            describe_features(specs)))

        runs_dir.joinpath("LATEST").write_text(run_id + "\n")
        o = metrics["overall"]
        ci = o["skill_interval"]["vs_raw_nwp"]
        logger.info(f"Test daylight MAE: ML {o['ml_model_p50']['mae']} | raw NWP {o['raw_nwp']['mae']} | "
                    f"persistence {o['persistence']['mae']} W/m²; skill vs NWP {o['ml_model_p50']['skill']}% "
                    f"[{ci['low']}, {ci['high']}]; coverage {o['p10_p90_coverage']}%")
        logger.info(f"Run written to {run_dir}")
        return run_dir
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()


def resolve_run(run_id: str | None, runs_dir: Path = RUNS_DIR) -> Path:
    if run_id is None:
        latest = runs_dir / "LATEST"
        if not latest.exists():
            raise FileNotFoundError("No runs yet. Run `python -m src.pipeline run` first.")
        run_id = latest.read_text().strip()
    path = runs_dir / run_id
    if not path.is_dir():
        raise FileNotFoundError(f"Run directory not found: {path}")
    return path


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.pipeline", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_ing = sub.add_parser("ingest", help="download raw data")
    p_ing.add_argument("--refresh", action="store_true", help="re-download even if cached")
    p_ing.add_argument("--no-nasa", action="store_true", help="skip the NASA POWER cross-check source")
    p_run = sub.add_parser("run", help="build dataset, train, evaluate")
    p_run.add_argument("--run-id")
    p_pub = sub.add_parser("publish", help="publish a run to the dashboards")
    p_pub.add_argument("--run-id")
    p_all = sub.add_parser("all", help="ingest, run and publish")
    p_all.add_argument("--refresh", action="store_true")
    sub.add_parser("contract-doc", help="regenerate the output contract document")
    for p in (parser, p_ing, p_run, p_pub, p_all):
        p.add_argument("--config", default=str(RUN_CONFIG_FILE), help=argparse.SUPPRESS)
        p.add_argument("--sites", default=str(SITES_CONFIG_FILE), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", stream=sys.stdout)
    for noisy in ("urllib3", "lightgbm"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if args.cmd == "contract-doc":
        CONTRACT_DOC.write_text(render_contract_markdown())
        logger.info(f"Wrote {CONTRACT_DOC}")
        return 0

    cfg = load_run_config(args.config)
    sites = load_and_validate_sites(args.sites)

    if args.cmd in ("ingest", "all"):
        ingest_all(sites, cfg, refresh=args.refresh, include_nasa=not getattr(args, "no_nasa", False))
    if args.cmd in ("run", "all"):
        run_dir = run(cfg, sites, getattr(args, "run_id", None) or make_run_id())
    if args.cmd == "publish":
        publish_run(resolve_run(args.run_id))
    if args.cmd == "all":
        publish_run(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
