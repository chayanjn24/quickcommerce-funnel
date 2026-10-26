"""Tests behind each finding in the README, plus the two README charts."""
import json

import matplotlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

from qcom.data import ENGINE, IMAGES, OUT
from qcom.stats import compare_proportions

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, RED = "#2a78d6", "#eb6834", "#e34948"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "text.color": INK, "font.size": 9, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": False, "grid.color": GRID, "grid.linewidth": 0.6,
})


def q(sql):
    with ENGINE.connect() as conn:
        return pd.read_sql(sql, conn)


def pct(x, digits=1):
    return f"{x * 100:.{digits}f}%"


def save(fig, name):
    IMAGES.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(IMAGES / name, dpi=170)
    plt.close(fig)


def amazon():
    orders = q("select * from marts.fct_amazon_orders")
    f = {}

    m = orders[orders.fulfilment == "Merchant"]
    a = orders[orders.fulfilment == "Amazon"]
    r = compare_proportions((a.outcome == "Cancelled").sum(), len(a), (m.outcome == "Cancelled").sum(), len(m))
    f["cancel_rate_amazon_fulfilled"] = r.rate_control
    f["cancel_rate_merchant_fulfilled"] = r.rate_treatment
    f["cancel_gap_ci95_pp"] = [r.ci_low * 100, r.ci_high * 100]
    f["cancel_gap_p"] = r.p_value

    b2b, cons = orders[orders.is_b2b], orders[~orders.is_b2b]
    r = compare_proportions((cons.outcome == "Cancelled").sum(), len(cons), (b2b.outcome == "Cancelled").sum(), len(b2b))
    f["cancel_rate_consumer"], f["cancel_rate_b2b"], f["b2b_orders"], f["b2b_vs_consumer_p"] = r.rate_control, r.rate_treatment, len(b2b), r.p_value

    f["orders"] = len(orders)
    f["overall_cancel_rate"] = float((orders.outcome == "Cancelled").mean())
    f["merchant_delivered_share_of_placed"] = float((m.outcome == "Delivered").mean())
    f["merchant_returned_share_of_placed"] = float((m.outcome == "Returned").mean())

    # returns only exist for the seller's own shipments
    shipped = m[m.reached_shipped]
    national = float((shipped.outcome == "Returned").mean())
    f["merchant_return_rate_national"] = national
    by_state = shipped.groupby("ship_state").agg(shipped=("order_id", "size"), returned=("outcome", lambda s: (s == "Returned").sum()))
    by_state = by_state[by_state.shipped >= 300].copy()
    by_state["rate"] = by_state.returned / by_state.shipped
    by_state["p"] = [stats.binomtest(int(k), int(n), national).pvalue for k, n in zip(by_state.returned, by_state.shipped)]
    by_state[["lo", "hi"]] = np.array([proportion_confint(k, n, method="wilson") for k, n in zip(by_state.returned, by_state.shipped)])
    alpha = 0.05 / len(by_state)  # Bonferroni across states tested
    by_state["flag_high"] = (by_state.p < alpha) & (by_state.rate > national)
    by_state["flag_low"] = (by_state.p < alpha) & (by_state.rate < national)
    f["states_tested"] = len(by_state)
    f["states_high_returns"] = {s: round(r, 4) for s, r in by_state[by_state.flag_high].rate.sort_values(ascending=False).items()}
    f["states_low_returns"] = {s: round(r, 4) for s, r in by_state[by_state.flag_low].rate.sort_values().items()}

    east = ["ASSAM", "BIHAR", "ODISHA", "JHARKHAND"]
    e, rest = shipped[shipped.ship_state.isin(east)], shipped[~shipped.ship_state.isin(east)]
    r = compare_proportions((rest.outcome == "Returned").sum(), len(rest), (e.outcome == "Returned").sum(), len(e))
    f["east4_return_rate"], f["rest_return_rate"], f["east4_shipped"] = r.rate_treatment, r.rate_control, len(e)
    f["east4_vs_rest_ci95_pp"], f["east4_vs_rest_p"] = [r.ci_low * 100, r.ci_high * 100], r.p_value

    # promotion leakage: the ID is only filled once an order goes through
    f["cancel_rate_with_promo"] = float((orders[orders.has_promotion].outcome == "Cancelled").mean())
    f["cancel_rate_without_promo"] = float((orders[~orders.has_promotion].outcome == "Cancelled").mean())
    f["duplicate_lines_dropped"] = int(q("select (select count(*) from raw.amazon_sale_report) - (select count(*) from staging.stg_amazon__order_lines) as n").n[0])
    f["merchant_cancelled_with_promo_share"] = float(m[m.outcome == "Cancelled"].has_promotion.mean())
    f["merchant_delivered_with_promo_share"] = float(m[m.outcome == "Delivered"].has_promotion.mean())

    chart_state_returns(by_state, national)
    return f


def chart_state_returns(by_state, national):
    s = by_state.sort_values("rate")
    fig, ax = plt.subplots(figsize=(7, 6.2))
    y = np.arange(len(s))
    colours = [ORANGE if f else BLUE for f in s.flag_high]
    ax.hlines(y, s.lo * 100, s.hi * 100, color=GRID, lw=3)
    ax.scatter(s.rate * 100, y, color=colours, s=36, zorder=3, edgecolor=SURFACE, linewidth=1.5)
    ax.axvline(national * 100, color=INK_2, lw=1, ls="--")
    ax.text(national * 100 + 0.2, len(s) - 0.4, f"all states {pct(national)}", color=INK_2, fontsize=8)
    ax.set_yticks(y, [st.title() for st in s.index])
    ax.set_xlabel("Merchant-shipped orders returned to seller (%), 95% CI")
    ax.set_title("Returns by state: orange = significantly above the national rate")
    ax.grid(axis="x")
    save(fig, "state_returns.png")


def blinkit():
    f = {}
    orders = q("select * from marts.fct_orders")
    customers = q("select * from marts.dim_customers")
    cohorts = q("select * from marts.cohorts")
    rfm = q("select * from marts.rfm")
    mkt = q("select * from staging.stg_blinkit__marketing_performance")

    f["orders"], f["customers"], f["buyers"] = len(orders), len(customers), int(customers.has_ordered.sum())
    f["first_order"], f["last_order"] = str(orders.ordered_at.min().date()), str(orders.ordered_at.max().date())
    f["repeat_buyer_share"] = float(customers[customers.has_ordered].is_repeat_customer.mean())
    f["median_days_between_orders"] = float(orders.days_since_previous_order.median())
    f["aov_inr"] = float(orders.order_total.mean())
    f["order_total_not_qty_x_price"] = int(q("""select count(*) as n from staging.stg_blinkit__orders o
        join staging.stg_blinkit__order_items i using (order_id)
        where abs(o.order_total - i.quantity * i.unit_price) >= 1""").n[0])
    f["reported_orders_wrong"] = int((customers.total_orders_reported != customers.orders).sum())
    f["first_order_before_registration"] = int(customers.registered_after_first_order.sum())

    # acquisition vs repeat
    orders["quarter"] = orders.ordered_at.dt.to_period("Q").astype(str)
    by_q = orders.groupby("quarter").agg(orders=("order_id", "size"), new=("is_first_order", "sum"))
    by_q["repeat_share"] = 1 - by_q.new / by_q.orders
    f["by_quarter"] = {k: {"orders": int(v.orders), "new_customers": int(v.new), "repeat_share": round(v.repeat_share, 4)} for k, v in by_q.iterrows()}
    new_by_month = customers[customers.has_ordered].groupby("cohort_month").size()
    f["new_customers_peak_month"] = {"month": str(new_by_month.idxmax()), "customers": int(new_by_month.max())}
    jul_oct_2024 = (new_by_month.index >= pd.Timestamp("2024-07-01").date()) & (new_by_month.index < pd.Timestamp("2024-11-01").date())
    f["new_customers_jul_oct_2024_avg"] = float(new_by_month[jul_oct_2024].mean())  # Nov 2024 has only 4 days

    # retention: flat or decaying?
    later = cohorts[(cohorts.months_since_first.between(1, 12))]
    wls = sm.WLS(later.retention.astype(float), sm.add_constant(later.months_since_first.astype(float)), weights=later.cohort_customers).fit()
    pooled = later.groupby("months_since_first").apply(lambda d: d.active_customers.sum() / d.cohort_customers.sum(), include_groups=False)
    f["retention_month1"], f["retention_month12"] = float(pooled.loc[1]), float(pooled.loc[12])
    f["retention_month1_to_12_range"] = [float(pooled.min()), float(pooled.max())]
    f["retention_slope_pp_per_month"], f["retention_slope_p"] = float(wls.params.iloc[1] * 100), float(wls.pvalues.iloc[1])

    # RFM
    seg = rfm.groupby("rfm_segment").agg(customers=("customer_id", "size"), revenue=("monetary", "sum"))
    seg["customer_share"], seg["revenue_share"] = seg.customers / seg.customers.sum(), seg.revenue / seg.revenue.sum()
    f["rfm"] = {k: {"customers": int(v.customers), "customer_share": round(v.customer_share, 4), "revenue_share": round(v.revenue_share, 4)} for k, v in seg.iterrows()}

    # reported segment labels vs behaviour
    table = pd.crosstab(rfm.segment_reported, rfm.rfm_segment)
    chi2, p, _, _ = stats.chi2_contingency(table)
    f["label_vs_rfm_cramers_v"] = float(np.sqrt(chi2 / (table.values.sum() * (min(table.shape) - 1))))
    f["label_vs_rfm_p"] = float(p)
    f["inactive_label_but_champion"] = int(table.loc["Inactive", "Champions"])

    # marketing funnel: does any campaign, channel or audience stand out?
    mkt["roas"] = mkt.revenue / mkt.spend
    mkt["ctr"] = mkt.clicks / mkt.impressions
    mkt["cvr"] = mkt.conversions / mkt.clicks.replace(0, np.nan)
    tot = mkt[["impressions", "clicks", "conversions", "spend", "revenue"]].sum()
    f["marketing"] = {
        "impressions": int(tot.impressions), "clicks": int(tot.clicks), "conversions": int(tot.conversions),
        "ctr": float(tot.clicks / tot.impressions), "click_to_conversion": float(tot.conversions / tot.clicks),
        "roas": float(tot.revenue / tot.spend),
        "roas_reported_mismatch_rows": int((abs(mkt.roas_reported - mkt.roas) > 0.01).sum()),
        "campaign_days": len(mkt),
    }
    for dim in ["campaign_name", "channel", "target_audience"]:
        for metric in ["roas", "ctr", "cvr"]:
            groups = [g[metric].dropna().to_numpy() for _, g in mkt.groupby(dim)]
            f["marketing"][f"kruskal_p_{metric}_by_{dim}"] = float(stats.kruskal(*groups).pvalue)
    chan = mkt.groupby("channel").agg(spend=("spend", "sum"), revenue=("revenue", "sum"))
    f["marketing"]["roas_by_channel"] = {k: float(v.revenue / v.spend) for k, v in chan.iterrows()}
    f["marketing"]["spend_by_channel"] = {k: float(v.spend) for k, v in chan.iterrows()}
    # bootstrap the ROAS gap between best and worst channel over campaign-days
    rng = np.random.default_rng(2026)
    best, worst = chan.eval("revenue / spend").idxmax(), chan.eval("revenue / spend").idxmin()
    b, w = mkt[mkt.channel == best], mkt[mkt.channel == worst]
    gaps = []
    for _ in range(2000):
        bi, wi = rng.integers(0, len(b), len(b)), rng.integers(0, len(w), len(w))
        gaps.append(b.revenue.values[bi].sum() / b.spend.values[bi].sum() - w.revenue.values[wi].sum() / w.spend.values[wi].sum())
    f["marketing"]["best_vs_worst_channel"] = {"best": best, "worst": worst, "roas_gap": float(chan.loc[best].revenue / chan.loc[best].spend - chan.loc[worst].revenue / chan.loc[worst].spend),
                                                "roas_gap_ci95": [float(np.percentile(gaps, 2.5)), float(np.percentile(gaps, 97.5))]}
    camp = mkt.groupby("campaign_name").apply(lambda d: d.revenue.sum() / d.spend.sum(), include_groups=False)
    f["marketing"]["roas_by_campaign_range"] = [float(camp.min()), float(camp.max())]

    # delivery promise
    f["on_time_rate"] = float((orders.delivery_status == "On Time").mean())
    f["badly_late_rate"] = float((orders.delivery_status == "Significantly Delayed").mean())
    for dim in ["distance_band", "category", "order_hour"]:
        table = pd.crosstab(orders[dim], orders.delivery_status == "On Time")
        f[f"on_time_by_{dim}_chi2_p"] = float(stats.chi2_contingency(table)[1])
    ratings = [g.rating.to_numpy() for _, g in orders.groupby("delivery_status")]
    f["rating_by_status"] = {k: float(v) for k, v in orders.groupby("delivery_status").rating.mean().items()}
    f["rating_by_status_kruskal_p"] = float(stats.kruskal(*ratings).pvalue)

    reorder = q("""
        select o.delivery_status,
               exists (select 1 from marts.fct_orders n where n.customer_id = o.customer_id
                       and n.ordered_at > o.ordered_at and n.ordered_at <= o.ordered_at + interval '60 days') as reordered
        from marts.fct_orders o
        where o.ordered_at <= (select max(ordered_at) - interval '60 days' from marts.fct_orders)""")
    f["reorder_60d_by_status"] = {k: float(v) for k, v in reorder.groupby("delivery_status").reordered.mean().items()}
    f["reorder_60d_by_status_chi2_p"] = float(stats.chi2_contingency(pd.crosstab(reorder.delivery_status, reorder.reordered))[1])

    chart_new_vs_repeat(orders)
    return f


def chart_new_vs_repeat(orders):
    o = orders[(orders.ordered_at >= "2023-04-01") & (orders.ordered_at < "2024-11-01")]
    m = o.groupby([o.ordered_at.dt.to_period("M"), "is_first_order"]).size().unstack(fill_value=0)
    x = np.arange(len(m))
    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.bar(x, m[False], color=BLUE, width=0.72, label="Repeat customers")
    ax.bar(x, m[True], bottom=m[False] + 2, color=ORANGE, width=0.72, label="First order")
    ax.set_xticks(x[::3], [p.strftime("%b %y") for p in m.index[::3]])
    ax.set_ylabel("Orders per month")
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left", ncols=2)
    ax.set_ylim(0, m.sum(axis=1).max() * 1.25)
    ax.set_title("Blinkit: orders hold steady while first orders fade")
    save(fig, "new_vs_repeat.png")


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    out = {"amazon": amazon(), "blinkit": blinkit()}
    (OUT / "findings.json").write_text(json.dumps(out, indent=2, default=float))
    print("findings written to data/out/findings.json")
    return out
