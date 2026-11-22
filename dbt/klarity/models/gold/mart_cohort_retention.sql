-- Monthly cohort retention. Cohort = month of a person's first order.
-- months_since_first = 0 is the cohort itself (retention 1.0).
-- LAG gives the change against the previous month inside the same cohort.
with orders as (
    select customer_unique_id, cast(date_trunc('month', purchased_at) as date) as order_month
    from {{ ref('fct_orders') }}
    where order_status not in ('canceled', 'unavailable') and customer_unique_id is not null
),
first_month as (
    select customer_unique_id, min(order_month) as cohort_month from orders group by customer_unique_id
),
activity as (
    select distinct o.customer_unique_id, f.cohort_month, o.order_month
    from orders as o join first_month as f using (customer_unique_id)
),
by_cohort as (
    select
        cohort_month,
        datediff('month', cohort_month, order_month)  as months_since_first,
        count(*)                                      as active_customers
    from activity
    group by cohort_month, datediff('month', cohort_month, order_month)
),
sized as (
    select *, max(case when months_since_first = 0 then active_customers end)
              over (partition by cohort_month) as cohort_size
    from by_cohort
)
select
    cohort_month,
    months_since_first,
    cohort_size,
    active_customers,
    round(active_customers * 1.0 / cohort_size, 4)                                      as retention_rate,
    active_customers - lag(active_customers) over (partition by cohort_month order by months_since_first)
                                                                                         as change_vs_previous_month
from sized
