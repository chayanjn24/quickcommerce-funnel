-- scored 1 to 5 on each of R, F and M, as of the day after the last order
with snapshot as (
    select max(ordered_at)::date + 1 as as_of from {{ ref('fct_orders') }}
),

base as (
    select
        c.customer_id,
        c.segment_reported,
        snapshot.as_of - c.last_order_at::date      as recency_days,
        c.orders                                    as frequency,
        c.revenue                                   as monetary
    from {{ ref('dim_customers') }} c
    cross join snapshot
    where c.has_ordered
),

scored as (
    select
        *,
        6 - ntile(5) over (order by recency_days)               as r_score,
        ntile(5) over (order by frequency, monetary)            as f_score,
        ntile(5) over (order by monetary)                       as m_score
    from base
)

select
    *,
    r_score::text || f_score::text || m_score::text             as rfm_code,
    case
        when r_score >= 4 and f_score >= 4                      then 'Champions'
        when r_score >= 3 and f_score >= 3                      then 'Loyal'
        when r_score >= 4 and f_score <= 2                      then 'New or promising'
        when r_score <= 2 and f_score >= 3                      then 'At risk'
        when r_score <= 2 and f_score <= 2                      then 'Hibernating'
        else 'Needs attention'
    end                                                         as rfm_segment
from scored
