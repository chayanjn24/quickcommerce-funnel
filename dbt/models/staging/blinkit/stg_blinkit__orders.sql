-- no timezone in the source, so timestamps are left as they are
select
    order_id::bigint                          as order_id,
    customer_id::bigint                       as customer_id,
    order_date::timestamp                     as ordered_at,
    promised_delivery_time::timestamp         as promised_at,
    actual_delivery_time::timestamp           as delivered_at,
    delivery_status,
    order_total::numeric(12, 2)               as order_total,
    payment_method,
    delivery_partner_id::bigint               as delivery_partner_id
from {{ source('blinkit', 'blinkit_orders') }}
