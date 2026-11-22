-- Does a late delivery hurt the review score? Orders are grouped by how late they were.
select
    case when days_late = 0 then '0 on time or early'
         when days_late <= 3 then '1-3 days late'
         when days_late <= 7 then '4-7 days late'
         else '8+ days late' end                                   as lateness_bucket,
    count(*)                                                       as orders,
    round(avg(hours_to_approval), 1)                               as avg_hours_to_approval,
    round(avg(hours_to_carrier), 1)                                as avg_hours_to_carrier,
    round(avg(hours_in_transit), 1)                                as avg_hours_in_transit,
    round(avg(review_score), 2)                                    as avg_review_score,
    round(avg(case when review_score = 1 then 1.0 else 0.0 end), 4) as share_one_star
from {{ ref('fct_orders') }}
where delivered_at is not null and estimated_delivery_at is not null and review_score is not null
group by 1
