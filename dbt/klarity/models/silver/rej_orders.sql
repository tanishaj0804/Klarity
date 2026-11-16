-- Orders rejected from Silver, with a reason. The same order can appear twice (two reasons).
select o.order_id::varchar as record_key, 'orphan_customer' as reason_code
from {{ ref('stg_orders') }} o
where not exists (select 1 from {{ ref('stg_customers') }} c where c.customer_id = o.customer_id)

union all

select o.order_id, 'impossible_timeline'
from {{ ref('stg_orders') }} o
where o.delivered_at < o.purchased_at
