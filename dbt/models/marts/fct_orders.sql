select
    order_id,
    customer_id,
    product_id,
    ordered_at,
    ordered_at::date                                as order_date,
    extract(hour from ordered_at)::int              as order_hour,
    trim(to_char(ordered_at, 'Day'))                as order_weekday,
    order_total,
    payment_method,
    category,
    units,
    customer_order_number,
    is_first_order,
    round(days_since_previous_order::numeric, 1)    as days_since_previous_order,
    promised_window_minutes::int                    as promised_window_minutes,
    minutes_vs_promise,
    minutes_vs_promise > 5                          as is_late,
    delivery_status,
    delay_reason,
    distance_km,
    case
        when distance_km < 1 then '0-1 km'
        when distance_km < 2 then '1-2 km'
        when distance_km < 3 then '2-3 km'
        when distance_km < 4 then '3-4 km'
        else '4-5 km'
    end                                             as distance_band,
    rating,
    sentiment,
    feedback_category
from {{ ref('int_blinkit__orders_enriched') }}
