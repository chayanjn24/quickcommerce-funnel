-- marts must add back up to the raw files
with checks as (
    select 'blinkit orders' as check_name,
           (select count(*) from {{ source('blinkit', 'blinkit_orders') }})::numeric as raw_value,
           (select count(*) from {{ ref('fct_orders') }})::numeric as mart_value
    union all
    select 'blinkit order_total',
           (select sum(order_total::numeric) from {{ source('blinkit', 'blinkit_orders') }}),
           (select sum(order_total) from {{ ref('fct_orders') }})
    union all
    select 'amazon orders',
           (select count(distinct order_id) from {{ source('amazon', 'amazon_sale_report') }}),
           (select count(*) from {{ ref('fct_amazon_orders') }})
    union all
    -- against staging, since the 7 duplicate lines are dropped there
    select 'amazon amount',
           (select sum(amount_inr) from {{ ref('stg_amazon__order_lines') }}),
           (select sum(amount_inr) from {{ ref('fct_amazon_orders') }})
    union all
    select 'marketing spend',
           (select sum(spend::numeric) from {{ source('blinkit', 'blinkit_marketing_performance') }}),
           (select sum(spend) from {{ ref('campaign_funnel') }})
)
select * from checks where raw_value is distinct from mart_value
