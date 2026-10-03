"""Feature availability at issue time: observations can never become features."""

import numpy as np
import pandas as pd
import pytest

from src.config import load_run_config
from src.dataset import build_dataset
from src.features import FeatureSpec, LeakageError, assert_issue_time_safe, build_features, feature_names
from tests.synthetic import TEST_SITES, make_run_config, write_raw


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("feat")
    write_raw(tmp / "raw")
    cfg = load_run_config(make_run_config(tmp))
    data, _ = build_dataset(TEST_SITES, cfg, tmp / "raw")
    return cfg, data


def test_features_do_not_change_when_observations_change(setup):
    """Leakage test: rewriting every ERA5 value (and everything derived from it) must not move any feature."""
    cfg, data = setup
    base, specs = build_features(data, cfg)
    names = feature_names(specs)

    tampered = data.copy()
    rng = np.random.default_rng(1)
    tampered["ghi_actual"] = rng.uniform(0, 1000, len(tampered))
    tampered["kt_actual"] = rng.uniform(0, 1.5, len(tampered))
    tampered["ghi_persistence"] = rng.uniform(0, 1000, len(tampered))
    after, _ = build_features(tampered, cfg)

    pd.testing.assert_frame_equal(base[names], after[names])


def test_no_observation_columns_in_feature_set(setup):
    cfg, data = setup
    _, specs = build_features(data, cfg)
    names = set(feature_names(specs))
    assert not names & {"ghi_actual", "kt_actual", "ghi_persistence", "ghi_nasa"}
    assert {s.source for s in specs} <= {"nwp", "geometry", "calendar", "site"}


def test_registry_rejects_observation_features():
    with pytest.raises(LeakageError):
        assert_issue_time_safe([FeatureSpec("lag_kt_1h", "observation", "observed kt one hour earlier")])
    with pytest.raises(LeakageError):
        assert_issue_time_safe([FeatureSpec("ghi_actual", "nwp", "mislabelled")])


def test_temporal_context_stays_within_the_day(setup):
    cfg, data = setup
    f, _ = build_features(data, cfg)
    s = f[f["site_id"] == "AAA"].sort_values("time_utc")
    first_hour = s.groupby("date").head(1)
    assert first_hour["ec_kt_m1"].isna().all()
    last_hour = s.groupby("date").tail(1)
    assert last_hour["ec_kt_p1"].isna().all()
