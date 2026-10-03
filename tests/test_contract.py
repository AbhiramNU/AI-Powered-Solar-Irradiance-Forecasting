"""The published dashboard data and the contract document stay consistent with src/contract.py."""

import json

import pytest

from src.config import CONTRACT_DOC, DASHBOARD_DATA_DIR, FRONTEND_DATA_DIR
from src.contract import render_contract_markdown
from src.publish import load_contract


def test_contract_document_is_generated_from_schema():
    assert CONTRACT_DOC.read_text() == render_contract_markdown(), \
        "Contract doc is stale: run `python -m src.pipeline contract-doc`"


def test_published_dashboard_data_satisfies_contract():
    if not (DASHBOARD_DATA_DIR / "metrics.json").exists():
        pytest.skip("nothing published yet")
    contract = load_contract(DASHBOARD_DATA_DIR)
    assert contract["metrics"]["overall"]["quantile_crossings"] == 0


def test_frontend_data_matches_published_metrics():
    if not (FRONTEND_DATA_DIR / "metrics.json").exists():
        pytest.skip("frontend data not exported")
    assert json.loads((FRONTEND_DATA_DIR / "metrics.json").read_text()) == json.loads((DASHBOARD_DATA_DIR / "metrics.json").read_text())
