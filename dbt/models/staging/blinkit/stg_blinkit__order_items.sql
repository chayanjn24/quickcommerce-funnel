select
    order_id::bigint                as order_id,
    product_id::bigint              as product_id,
    quantity::int                   as quantity,
    unit_price::numeric(12, 2)      as unit_price
from {{ source('blinkit', 'blinkit_order_items') }}
