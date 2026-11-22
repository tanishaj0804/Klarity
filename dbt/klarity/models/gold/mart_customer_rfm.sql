-- RFM scoring per real person (customer_unique_id). Each score is 1 (worst) to 5 (best).
--   Recency  : days since the last purchase, measured from the newest order in the data (not today),
--              so the result does not change when you run it later. NTILE(5) over the whole base.
--   Frequency: number of orders. About 97 percent buy once, so NTILE would be meaningless: fixed steps.
--   Monetary : total order value, NTILE(5) over the whole base.
with orders as (
    select o.customer_unique_id, o.order_id, o.purchased_at, o.order_value
    from {{ ref('fct_orders') }} as o
    where o.order_status not in ('canceled', 'unavailable') and o.customer_unique_id is not null
),
as_of as (select max(purchased_at) as as_of_ts from orders),
per_customer as (
    select
        customer_unique_id,
        max(purchased_at)                                    as last_purchase_at,
        count(distinct order_id)                             as frequency,
        sum(order_value)                                     as monetary
    from orders
    group by customer_unique_id
),
scored as (
    select
        c.*,
        datediff('day', c.last_purchase_at, a.as_of_ts)      as recency_days,
        6 - ntile(5) over (order by datediff('day', c.last_purchase_at, a.as_of_ts))  as r_score,
        case when c.frequency >= 4 then 5 when c.frequency = 3 then 4
             when c.frequency = 2 then 3 else 1 end          as f_score,
        ntile(5) over (order by c.monetary)                  as m_score
    from per_customer as c cross join as_of as a
)
select
    *,
    case
        when r_score >= 4 and f_score >= 3 then 'champions'
        when f_score >= 3                  then 'loyal'
        when r_score <= 2 and m_score >= 4 then 'at_risk_big_spender'
        when m_score >= 4 and r_score >= 3 then 'big_spender'
        when r_score = 5                   then 'new'
        when r_score <= 2                  then 'hibernating'
        else 'regular'
    end as segment
from scored
