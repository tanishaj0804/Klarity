-- One row per calendar day from the first purchase to the last estimated delivery.
with recursive bounds as (
    select
        cast(min(purchased_at) as date) as first_day,
        cast(greatest(max(purchased_at), max(estimated_delivery_at)) as date) as last_day
    from {{ ref('slv_orders') }}
),
days as (
    select first_day as date_day, last_day from bounds
    union all
    select date_day + 1, last_day from days where date_day < last_day
)
select
    date_day                                    as date_key,
    year(date_day)                              as year,
    quarter(date_day)                           as quarter,
    month(date_day)                             as month,
    cast(date_trunc('month', date_day) as date) as month_start,
    cast(date_trunc('week', date_day) as date)  as week_start,
    dayofweek(date_day)                         as day_of_week,
    dayofweek(date_day) in (0, 6)               as is_weekend
from days
