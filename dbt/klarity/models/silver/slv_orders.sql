-- Clean orders: rejected ones removed (they are in slv_quarantine), delivery measures added.
select
    o.order_id,
    o.customer_id,
    o.order_status,
    o.purchased_at,
    o.approved_at,
    o.delivered_to_carrier_at,
    o.delivered_at,
    o.estimated_delivery_at,
    datediff('day', o.purchased_at, o.delivered_at)           as delivery_days,
    case when o.delivered_at is not null and o.estimated_delivery_at is not null
         then o.delivered_at > o.estimated_delivery_at end    as is_late
from {{ ref('stg_orders') }} o
where not exists (select 1 from {{ ref('rej_orders') }} r where r.record_key = o.order_id)
