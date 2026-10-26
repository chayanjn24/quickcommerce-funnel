-- Amazon-fulfilled orders never go past "Shipped" in this report, only the seller's own shipments show delivery
select
    order_id,
    ordered_on,
    date_trunc('month', ordered_on)::date                       as order_month,
    status,
    case
        when status = 'Cancelled'                                   then 'Cancelled'
        when status like 'Pending%'                                 then 'Pending'
        when status = 'Shipped - Delivered to Buyer'                then 'Delivered'
        when status in ('Shipped - Returned to Seller',
                        'Shipped - Returning to Seller',
                        'Shipped - Rejected by Buyer')              then 'Returned'
        when status in ('Shipped - Lost in Transit',
                        'Shipped - Damaged')                        then 'Lost or damaged'
        else 'Shipped'
    end                                                         as outcome,
    fulfilment,
    ship_service_level,
    sales_channel,
    ship_state,
    ship_city,
    is_b2b,
    has_promotion,
    category,
    lines,
    units,
    amount_inr,
    status <> 'Cancelled'                                       as reached_confirmed,
    status like 'Shipp%'                                        as reached_shipped,
    status = 'Shipped - Delivered to Buyer'                     as reached_delivered
from {{ ref('int_amazon__orders') }}
