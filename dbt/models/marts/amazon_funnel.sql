-- placed -> confirmed -> shipped, plus delivered for the seller's own shipments
with base as (
    select 'All orders' as segment, * from {{ ref('fct_amazon_orders') }}
    union all
    select fulfilment || '-fulfilled', * from {{ ref('fct_amazon_orders') }}
),

stages as (
    select segment, 1 as stage_order, 'Placed' as stage, count(*) as orders, sum(amount_inr) as amount_inr from base group by 1
    union all
    select segment, 2, 'Confirmed', count(*) filter (where reached_confirmed), sum(amount_inr) filter (where reached_confirmed) from base group by 1
    union all
    select segment, 3, 'Shipped', count(*) filter (where reached_shipped), sum(amount_inr) filter (where reached_shipped) from base group by 1
    union all
    select segment, 4, 'Delivered', count(*) filter (where reached_delivered), sum(amount_inr) filter (where reached_delivered)
    from base where segment = 'Merchant-fulfilled' group by 1
)

select
    segment,
    stage_order,
    stage,
    orders,
    amount_inr,
    round(orders::numeric / first_value(orders) over w, 4)          as share_of_placed,
    round(orders::numeric / lag(orders) over w, 4)                  as share_of_previous
from stages
window w as (partition by segment order by stage_order)
