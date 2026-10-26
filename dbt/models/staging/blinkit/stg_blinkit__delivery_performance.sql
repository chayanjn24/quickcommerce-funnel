select
    order_id::bigint                        as order_id,
    promised_time::timestamp                as promised_at,
    actual_time::timestamp                  as delivered_at,
    delivery_time_minutes::numeric::int     as minutes_vs_promise,
    distance_km::numeric(6, 2)              as distance_km,
    delivery_status,
    nullif(trim(reasons_if_delayed), '')    as delay_reason
from {{ source('blinkit', 'blinkit_delivery_performance') }}
