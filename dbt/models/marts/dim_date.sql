-- covers both sources: Amazon 2022 and Blinkit 2023-24
with bounds as (
    select least(
               (select min(ordered_at)::date from {{ ref('stg_blinkit__orders') }}),
               (select min(ordered_on) from {{ ref('stg_amazon__order_lines') }})
           ) as start_date,
           greatest(
               (select max(ordered_at)::date from {{ ref('stg_blinkit__orders') }}),
               (select max(campaign_date) from {{ ref('stg_blinkit__marketing_performance') }})
           ) as end_date
)

select
    d::date                                 as date_day,
    date_trunc('week', d)::date             as week_start,
    date_trunc('month', d)::date            as month_start,
    extract(year from d)::int               as year,
    extract(quarter from d)::int            as quarter,
    trim(to_char(d, 'Day'))                 as weekday,
    extract(isodow from d) in (6, 7)        as is_weekend
from bounds, generate_series(start_date, end_date, interval '1 day') d
