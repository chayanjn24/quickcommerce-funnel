with items as (
    select
        i.order_id,
        count(*)                                    as item_lines,
        sum(i.quantity)                             as units,
        sum(i.quantity * i.unit_price)              as items_value,
        min(p.category)                             as category,
        min(i.product_id)                           as product_id
    from {{ ref('stg_blinkit__order_items') }} i
    join {{ ref('stg_blinkit__products') }} p using (product_id)
    group by 1
),

numbered as (
    select
        o.*,
        row_number() over (partition by o.customer_id order by o.ordered_at, o.order_id) as customer_order_number,
        lag(o.ordered_at) over (partition by o.customer_id order by o.ordered_at, o.order_id) as previous_order_at
    from {{ ref('stg_blinkit__orders') }} o
)

select
    o.order_id,
    o.customer_id,
    o.ordered_at,
    o.promised_at,
    o.delivered_at,
    o.delivery_status,
    o.order_total,
    o.payment_method,
    o.delivery_partner_id,
    o.customer_order_number,
    o.customer_order_number = 1                                     as is_first_order,
    extract(epoch from o.ordered_at - o.previous_order_at) / 86400  as days_since_previous_order,
    extract(epoch from o.promised_at - o.ordered_at) / 60           as promised_window_minutes,
    d.minutes_vs_promise,
    d.distance_km,
    d.delay_reason,
    i.item_lines,
    i.units,
    i.items_value,
    i.category,
    i.product_id,
    f.rating,
    f.sentiment,
    f.feedback_category
from numbered o
left join items i using (order_id)
left join {{ ref('stg_blinkit__delivery_performance') }} d using (order_id)
left join {{ ref('stg_blinkit__customer_feedback') }} f using (order_id)
