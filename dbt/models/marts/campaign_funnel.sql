select
    date_trunc('month', campaign_date)::date            as month_start,
    campaign_name,
    channel,
    target_audience,
    count(*)                                            as campaign_days,
    sum(impressions)                                    as impressions,
    sum(clicks)                                         as clicks,
    sum(conversions)                                    as conversions,
    sum(spend)                                          as spend,
    sum(revenue)                                        as revenue,
    round(sum(clicks)::numeric / nullif(sum(impressions), 0), 4)        as ctr,
    round(sum(conversions)::numeric / nullif(sum(clicks), 0), 4)        as click_to_conversion,
    round(sum(conversions)::numeric / nullif(sum(impressions), 0), 5)   as impression_to_conversion,
    round(sum(revenue) / nullif(sum(spend), 0), 3)                      as roas,
    round(sum(spend) / nullif(sum(conversions), 0), 2)                  as cost_per_conversion
from {{ ref('stg_blinkit__marketing_performance') }}
group by 1, 2, 3, 4
