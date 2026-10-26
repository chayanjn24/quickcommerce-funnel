with orders as (
    select
        customer_id,
        min(ordered_at)         as first_order_at,
        max(ordered_at)         as last_order_at,
        count(*)                as orders,
        sum(order_total)        as revenue
    from {{ ref('stg_blinkit__orders') }}
    group by 1
)

select
    c.customer_id,
    c.area,
    c.pincode,
    c.registered_on,
    c.segment_reported,
    o.first_order_at,
    o.last_order_at,
    date_trunc('month', o.first_order_at)::date             as cohort_month,
    coalesce(o.orders, 0)                                   as orders,
    coalesce(o.revenue, 0)                                  as revenue,
    round(o.revenue / nullif(o.orders, 0), 2)               as avg_order_value,
    o.orders is not null                                    as has_ordered,
    o.orders > 1                                            as is_repeat_customer,
    c.registered_on > o.first_order_at::date                as registered_after_first_order,
    c.total_orders_reported,
    c.avg_order_value_reported
from {{ ref('stg_blinkit__customers') }} c
left join orders o using (customer_id)
