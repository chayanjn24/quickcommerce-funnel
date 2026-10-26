select
    product_id::bigint                      as product_id,
    product_name,
    category,
    brand,
    price::numeric(12, 2)                   as price,
    mrp::numeric(12, 2)                     as mrp,
    margin_percentage::numeric(5, 2)        as margin_pct,
    shelf_life_days::int                    as shelf_life_days
from {{ source('blinkit', 'blinkit_products') }}
