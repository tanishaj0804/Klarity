
-- Daily order count with a 7-day rolling z-score.
-- The window covers the 7 days BEFORE the day.
-- The day itself is not included in its baseline.
-- |z| > 3 is flagged as an anomaly.

with daily as (
    select
        d.date_key,
        count(o.order_id) as orders
    from {{ ref('dim_date') }} as d
    left join {{ ref('fct_orders') }} as o
        on o.purchase_date = d.date_key
    where d.date_key <= (
        select max(purchase_date)
        from {{ ref('fct_orders') }}
    )
    group by d.date_key
),

rolled as (
    select
        date_key,
        orders,
        avg(orders) over (
            order by date_key
            rows between 7 preceding and 1 preceding
        ) as rolling_avg_7d,

        stddev_samp(orders) over (
            order by date_key
            rows between 7 preceding and 1 preceding
        ) as rolling_std_7d,

        count(*) over (
            order by date_key
            rows between 7 preceding and 1 preceding
        ) as days_in_window

    from daily
),

scored as (
    select
        *,
        case
            when days_in_window = 7
            then (orders - rolling_avg_7d) / nullif(rolling_std_7d, 0)
        end as z_score
    from rolled
)

select
    *,
    coalesce(
        days_in_window = 7
        and abs(z_score) > 3,
        false
    ) as is_anomaly
from scored
