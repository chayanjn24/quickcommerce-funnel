-- no promotion slice on purpose: promotion_ids only get filled once an order goes through,
-- so cancelled orders almost never have one and it looks like promotions stop cancellations
with o as (select * from {{ ref('fct_amazon_orders') }}),

slices as (
    select 'State' as dimension, ship_state as value, * from o
    union all
    select 'Category', category, * from o
    union all
    select 'Fulfilment', fulfilment, * from o
    union all
    select 'Customer type', case when is_b2b then 'B2B' else 'Consumer' end, * from o
    union all
    select 'Month', to_char(order_month, 'YYYY-MM'), * from o
)

select
    dimension,
    value,
    count(*)                                                                as orders,
    count(*) filter (where outcome = 'Cancelled')                           as cancelled,
    round(avg((outcome = 'Cancelled')::int), 4)                             as cancel_rate,
    count(*) filter (where fulfilment = 'Merchant' and reached_shipped)     as merchant_shipped,
    count(*) filter (where outcome = 'Returned')                            as returned,
    round(
        count(*) filter (where outcome = 'Returned')::numeric
        / nullif(count(*) filter (where fulfilment = 'Merchant' and reached_shipped), 0), 4
    )                                                                       as merchant_return_rate,
    sum(amount_inr) filter (where outcome <> 'Cancelled')                   as kept_amount_inr
from slices
group by 1, 2
