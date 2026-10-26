select
    product_id,
    product_name,
    category,
    brand,
    price,
    mrp,
    margin_pct,
    shelf_life_days
from {{ ref('stg_blinkit__products') }}
