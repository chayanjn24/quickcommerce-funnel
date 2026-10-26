select
    feedback_id::bigint             as feedback_id,
    order_id::bigint                as order_id,
    customer_id::bigint             as customer_id,
    rating::int                     as rating,
    feedback_text,
    feedback_category,
    sentiment,
    feedback_date::date             as feedback_on
from {{ source('blinkit', 'blinkit_customer_feedback') }}
