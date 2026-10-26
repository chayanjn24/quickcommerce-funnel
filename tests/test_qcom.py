import json

import numpy as np
import pytest
from sqlalchemy import text

from qcom.data import ENGINE, OUT
from qcom.stats import bootstrap_diff_ci, compare_proportions, mde_relative, required_n_per_arm, srm_check


def test_srm_check():
    assert srm_check(5000, 5000) == pytest.approx(1.0)
    assert srm_check(15051, 14306) < 0.001


def test_sample_size_matches_textbook():
    # 10% -> 12% at alpha 0.05 and 80% power needs about 3,840 per arm
    assert 3800 <= required_n_per_arm(0.10, 0.20) <= 3900
    assert mde_relative(0.0955, required_n_per_arm(0.0955, 0.10)) == pytest.approx(0.10, abs=0.002)


def test_compare_proportions():
    r = compare_proportions(100, 1000, 130, 1000)
    assert r.abs_diff == pytest.approx(0.03)
    assert r.rel_lift == pytest.approx(0.30)
    assert r.ci_low < 0.03 < r.ci_high and r.p_value < 0.05
    same = compare_proportions(100, 1000, 100, 1000)
    assert same.ci_low < 0 < same.ci_high and same.p_value == pytest.approx(1.0)


def test_bootstrap_ci_contains_truth():
    rng = np.random.default_rng(1)
    low, high = bootstrap_diff_ci(rng.normal(100, 10, 4000), rng.normal(105, 10, 4000), seed=1)
    assert low < 5 < high


# The checks below need `python run.py` to have run.

def test_marts_are_built():
    with ENGINE.connect() as conn:
        for table in ["marts.fct_orders", "marts.fct_amazon_orders", "marts.cohorts", "marts.rfm",
                      "marts.campaign_funnel", "marts.experiment_users"]:
            assert conn.execute(text(f"select count(*) from {table}")).scalar() > 0, table


def test_experiment_recovers_the_true_effect():
    out = json.loads((OUT / "experiment.json").read_text())
    low, high = out["results"]["clean"]["reorder_rel_lift_ci95"]
    assert low < out["truth"]["relative_lift"] < high
    assert out["results"]["srm_bug"]["srm_ok"] is False
    assert abs(out["validation"]["aa_false_positive_rate"] - 0.05) < 0.015
