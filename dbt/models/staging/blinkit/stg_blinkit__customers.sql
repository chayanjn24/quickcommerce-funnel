-- names, emails, phones and addresses dropped, nothing needs them
-- total_orders and avg_order_value don't match the orders table, so dim_customers recounts them
select
    customer_id::bigint                     as customer_id,
    area,
    pincode,
    registration_date::date                 as registered_on,
    customer_segment                        as segment_reported,
    total_orders::int                       as total_orders_reported,
    avg_order_value::numeric(12, 2)         as avg_order_value_reported
from {{ source('blinkit', 'blinkit_customers') }}
