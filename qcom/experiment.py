"""Simulated win-back test: customers lapsed 60+ days get Rs 100 off their next order.

Base rate and basket sizes come from the Blinkit orders; the true effect is set below so I can
check the analysis finds it. Rule decided up front: ship only if the lift's 95% CI is above zero
and net revenue per user doesn't drop more than 2%.
"""
import json

import numpy as np
import pandas as pd
from sqlalchemy import text

from qcom import findings
from qcom.data import ENGINE, IMAGES, OUT
from qcom.stats import bootstrap_diff_ci, compare_proportions, mde_relative, required_n_per_arm, srm_check

SEED = 2026
USERS = 30_000                 # split 50/50
TRUE_RELATIVE_LIFT = 0.12
TRUE_BASKET_EFFECT = -0.02     # discounted baskets are 2% smaller
DISCOUNT_INR = 100
SECOND_ORDER_RATE = 0.05
OLD_APP_SHARE = 0.08           # old-app users reorder less (x0.6) and, in the buggy run,
OLD_APP_RATE_FACTOR = 0.6      # half of treatment old-app users lose their exposure log
OLD_APP_LOGGING_LOSS = 0.5

SRM_ALPHA = 0.001
GUARDRAIL_FLOOR = -0.02
PLANNED_LIFT = 0.10            # smallest lift worth the discount, chosen before the test
VALIDATION_RUNS = 2000

# For each month start from Jul 2023 to Sep 2024: customers whose last order is 60+ days old.
# Did they order in the next 30 days?
BASELINE_SQL = """
with refs as (
    select generate_series('2023-07-01'::date, '2024-09-01'::date, interval '1 month')::date as ref
),
lapsed as (
    select r.ref, o.customer_id
    from refs r join marts.fct_orders o on o.ordered_at < r.ref
    group by 1, 2
    having max(o.ordered_at) < r.ref - interval '60 days'
)
select
    count(*) as customer_months,
    avg(case when exists (
            select 1 from marts.fct_orders n
            where n.customer_id = l.customer_id
              and n.ordered_at >= l.ref and n.ordered_at < l.ref + interval '30 days'
        ) then 1.0 else 0.0 end) as reorder_30d,
    count(*) filter (where ref = '2024-09-01') as lapsed_last_month
from lapsed l
"""

MARGIN_SQL = """
select avg(o.order_total * p.margin_pct / 100) as margin_per_order
from marts.fct_orders o join marts.dim_products p using (product_id)
"""


def simulate():
    rng = np.random.default_rng(SEED)
    with ENGINE.connect() as conn:
        baseline = float(conn.execute(text(BASELINE_SQL)).one().reorder_30d)
        baskets = pd.read_sql("select order_total from marts.fct_orders", conn)["order_total"].to_numpy(float)

    users = pd.DataFrame({"user_id": np.arange(1, USERS + 1)})
    users["variant"] = np.where(rng.random(USERS) < 0.5, "control", "treatment")
    users["app_version"] = np.where(rng.random(USERS) < OLD_APP_SHARE, "old", "current")

    # scale the current-app rate so the blended control rate equals the real baseline
    current = baseline / (1 - OLD_APP_SHARE + OLD_APP_SHARE * OLD_APP_RATE_FACTOR)
    rate = np.where(users.app_version == "old", current * OLD_APP_RATE_FACTOR, current)
    rate = np.where(users.variant == "treatment", rate * (1 + TRUE_RELATIVE_LIFT), rate)
    order_count = np.where(rng.random(USERS) < rate, 1 + (rng.random(USERS) < SECOND_ORDER_RATE), 0)

    rows = []
    for user_id, variant, n in zip(users.user_id, users.variant, order_count):
        for k in range(n):
            basket = rng.choice(baskets) * (1 + TRUE_BASKET_EFFECT if variant == "treatment" else 1)
            discount = DISCOUNT_INR if variant == "treatment" and k == 0 else 0
            rows.append((user_id, k + 1, int(rng.integers(0, 30)), round(basket, 2), discount))
    orders = pd.DataFrame(rows, columns=["user_id", "order_number", "day_in_window", "basket_inr", "discount_inr"])

    lost = (users.variant == "treatment") & (users.app_version == "old") & (rng.random(USERS) < OLD_APP_LOGGING_LOSS)
    buggy = users[~lost]
    all_users = pd.concat([users.assign(scenario="clean"), buggy.assign(scenario="srm_bug")])
    all_orders = pd.concat([orders.assign(scenario="clean"),
                            orders[orders.user_id.isin(buggy.user_id)].assign(scenario="srm_bug")])
    all_users.to_sql("ab_users", ENGINE, schema="raw", if_exists="replace", index=False)
    all_orders.to_sql("ab_orders", ENGINE, schema="raw", if_exists="replace", index=False)
    print(f"simulated {USERS:,} users (baseline {baseline:.2%}); the buggy run lost {lost.sum():,} treatment users")


def read_scenario(df):
    c, t = df[df.variant == "control"], df[df.variant == "treatment"]
    srm_p = srm_check(len(c), len(t))
    r = compare_proportions(int(c.reordered.sum()), len(c), int(t.reordered.sum()), len(t))
    net_c, net_t = c.net_inr.to_numpy(float), t.net_inr.to_numpy(float)
    net_ci = bootstrap_diff_ci(net_c, net_t, seed=SEED, relative=True)
    srm_ok = srm_p >= SRM_ALPHA
    ship = srm_ok and r.ci_low > 0 and net_ci[0] > GUARDRAIL_FLOOR
    return {
        "users_control": len(c), "users_treatment": len(t),
        "srm_p_value": srm_p, "srm_ok": srm_ok,
        "reorder_rate_control": r.rate_control, "reorder_rate_treatment": r.rate_treatment,
        "reorder_abs_diff": r.abs_diff, "reorder_rel_lift": r.rel_lift,
        "reorder_diff_ci95": [r.ci_low, r.ci_high],
        "reorder_rel_lift_ci95": [r.ci_low / r.rate_control, r.ci_high / r.rate_control],
        "reorder_p_value": r.p_value,
        "net_per_user_control": float(net_c.mean()), "net_per_user_treatment": float(net_t.mean()),
        "net_per_user_rel_change": float(net_t.mean() / net_c.mean() - 1), "net_per_user_rel_ci95": list(net_ci),
        "aov_control": float(c.gross_inr.sum() / c.orders.sum()), "aov_treatment": float(t.gross_inr.sum() / t.orders.sum()),
        "decision": "ship" if ship else ("not readable: sample ratio mismatch" if not srm_ok else "do not ship"),
    }


def validate(baseline, n_per_arm, rng):
    """Re-run the test 2,000 times with known truth: false-positive rate, power and CI coverage."""
    def run(rate_t):
        x_c = rng.binomial(n_per_arm, baseline, VALIDATION_RUNS)
        x_t = rng.binomial(n_per_arm, rate_t, VALIDATION_RUNS)
        res = [compare_proportions(int(a), n_per_arm, int(b), n_per_arm) for a, b in zip(x_c, x_t)]
        return (np.mean([x.p_value < 0.05 for x in res]),
                np.mean([x.ci_low <= rate_t - baseline <= x.ci_high for x in res]))

    aa_fpr, _ = run(baseline)
    power, coverage = run(baseline * (1 + TRUE_RELATIVE_LIFT))
    return {"runs": VALIDATION_RUNS, "aa_false_positive_rate": float(aa_fpr),
            "power_at_true_lift": float(power), "ci95_coverage": float(coverage)}


def analyse():
    with ENGINE.connect() as conn:
        base = conn.execute(text(BASELINE_SQL)).one()
        margin = float(conn.execute(text(MARGIN_SQL)).scalar())
        df = pd.read_sql("select * from marts.experiment_users", conn)
    baseline = float(base.reorder_30d)
    results = {name: read_scenario(g) for name, g in df.groupby("scenario")}
    clean = results["clean"]

    control_net = df.query("scenario == 'clean' and variant == 'control'").net_inr.astype(float)
    cv = control_net.std() / control_net.mean()
    plan = {
        "baseline_reorder_30d": baseline,
        "baseline_customer_months": int(base.customer_months),
        "required_users_per_arm_for_10pct": required_n_per_arm(baseline, PLANNED_LIFT),
        "mde_at_test_size": mde_relative(baseline, USERS // 2),
        "real_lapsed_pool": int(base.lapsed_last_month),
        "mde_at_real_pool": mde_relative(baseline, int(base.lapsed_last_month) // 2),
        # users per arm for a +/-2% CI on net revenue per user (normal approximation)
        "users_per_arm_for_2pct_revenue_ci": int(np.ceil(2 * (1.96 * cv / abs(GUARDRAIL_FLOOR)) ** 2)),
    }

    # The discount goes to every returning treatment user, including those who would have come back anyway.
    discount_per_user = float(df.query("scenario == 'clean' and variant == 'treatment'").discount_inr.mean())
    low, high = clean["reorder_diff_ci95"]
    economics = {
        "margin_per_order_inr": margin,
        "discount_per_treated_user_inr": discount_per_user,
        "cost_per_extra_reorder_inr": discount_per_user / clean["reorder_abs_diff"],
        "cost_per_extra_reorder_ci95_inr": [discount_per_user / high, discount_per_user / low],
        "break_even_rel_lift": discount_per_user / margin / clean["reorder_rate_control"],
    }
    out = {"plan": plan, "truth": {"relative_lift": TRUE_RELATIVE_LIFT}, "results": results,
           "economics": economics, "validation": validate(baseline, USERS // 2, np.random.default_rng(SEED))}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "experiment.json").write_text(json.dumps(out, indent=2))
    chart(results, economics["break_even_rel_lift"])
    print(f"clean test: lift {clean['reorder_rel_lift']:+.1%}, decision: {clean['decision']}; "
          f"buggy test: {results['srm_bug']['decision']}")
    return out


def chart(results, break_even):
    plt = findings.plt
    fig, ax = plt.subplots(figsize=(8, 3.2))
    rows = [("Clean test", results["clean"]), ("Test with logging bug", results["srm_bug"])]
    for i, (_, r) in enumerate(rows):
        low, high = r["reorder_rel_lift_ci95"]
        lift = r["reorder_rel_lift"]
        colour = findings.BLUE if r["srm_ok"] else findings.RED
        ax.errorbar(lift * 100, i, xerr=[[(lift - low) * 100], [(high - lift) * 100]], fmt="o", color=colour, capsize=5, lw=2)
        note = "" if r["srm_ok"] else "  (sample ratio mismatch: not readable)"
        ax.text(high * 100 + 1, i, f"{lift:+.1%}{note}", va="center", fontsize=9)
    ax.axvline(TRUE_RELATIVE_LIFT * 100, color=findings.INK_2, ls="--", lw=1)
    ax.text(TRUE_RELATIVE_LIFT * 100 + 0.3, 1.5, "true effect", fontsize=8, color=findings.INK_2)
    ax.axvline(break_even * 100, color=findings.INK_2, ls=":", lw=1.2)
    ax.text(break_even * 100 + 0.3, -0.45, f"break-even for Rs {DISCOUNT_INR} off: {break_even:+.1%}", fontsize=8, color=findings.INK_2)
    ax.axvline(0, color=findings.GRID, lw=1)
    ax.set_yticks([0, 1], [r[0] for r in rows])
    ax.set_ylim(-0.6, 1.7)
    ax.set_xlabel("Relative lift in 30-day reorder rate (%), 95% CI")
    ax.set_title("Win-back offer: lift in 30-day reorder rate")
    findings.save(fig, "experiment.png")
