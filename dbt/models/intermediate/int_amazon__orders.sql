-- all lines of an order share the same status and address, so min() just picks one
with lines as (
    select * from {{ ref('stg_amazon__order_lines') }}
)

select
    order_id,
    min(ordered_on)                                     as ordered_on,
    min(status)                                         as status,
    min(fulfilment)                                     as fulfilment,
    min(ship_service_level)                             as ship_service_level,
    min(sales_channel)                                  as sales_channel,
    min(ship_state)                                     as ship_state,
    min(ship_city)                                      as ship_city,
    bool_or(is_b2b)                                     as is_b2b,
    bool_or(has_promotion)                              as has_promotion,
    count(*)                                            as lines,
    sum(qty)                                            as units,
    sum(coalesce(amount_inr, 0))                        as amount_inr,
    case when count(distinct category) = 1 then min(category) else 'Mixed' end as category
from lines
group by order_id
