select
    scenario,
    user_id::bigint                 as user_id,
    order_number::int               as order_number,
    day_in_window::int              as day_in_window,
    basket_inr::numeric(12, 2)      as basket_inr,
    discount_inr::numeric(12, 2)    as discount_inr
from {{ source('experiment', 'ab_orders') }}
