"""Small A/B test helpers."""
from types import SimpleNamespace

import numpy as np
from scipy import stats
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import confint_proportions_2indep, proportion_effectsize, proportions_ztest


def srm_check(n_control, n_treatment):
    """p-value for the split against the planned 50/50. Tiny p = something broke in assignment."""
    total = n_control + n_treatment
    return float(stats.chisquare([n_control, n_treatment], f_exp=[total / 2, total / 2]).pvalue)


def required_n_per_arm(baseline, lift, alpha=0.05, power=0.8):
    effect = proportion_effectsize(baseline * (1 + lift), baseline)
    return int(np.ceil(NormalIndPower().solve_power(effect_size=effect, alpha=alpha, power=power)))


def mde_relative(baseline, n_per_arm, alpha=0.05, power=0.8):
    """Smallest relative lift this many users per group can detect (inverts Cohen's h)."""
    h = NormalIndPower().solve_power(nobs1=n_per_arm, alpha=alpha, power=power)
    return float(np.sin(h / 2 + np.arcsin(np.sqrt(baseline))) ** 2 / baseline - 1)


def compare_proportions(x_c, n_c, x_t, n_t):
    """z-test plus a Newcombe 95% CI on treatment minus control."""
    p_c, p_t = x_c / n_c, x_t / n_t
    _, p = proportions_ztest([x_t, x_c], [n_t, n_c])
    low, high = confint_proportions_2indep(x_t, n_t, x_c, n_c, method="newcomb", compare="diff")
    return SimpleNamespace(rate_control=p_c, rate_treatment=p_t, abs_diff=p_t - p_c, rel_lift=p_t / p_c - 1,
                           ci_low=float(low), ci_high=float(high), p_value=float(p))


def bootstrap_diff_ci(control, treatment, n_boot=2000, seed=0, relative=False):
    rng = np.random.default_rng(seed)
    c = rng.choice(control, (n_boot, control.size)).mean(axis=1)
    t = rng.choice(treatment, (n_boot, treatment.size)).mean(axis=1)
    diffs = t / c - 1 if relative else t - c
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))
