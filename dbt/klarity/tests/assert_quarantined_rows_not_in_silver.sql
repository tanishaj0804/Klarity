-- A row listed in quarantine for the orders table must not also be in slv_orders.
select q.record_key
from {{ ref('slv_quarantine') }} q
join {{ ref('slv_orders') }} o on o.order_id = q.record_key
where q.source_table = 'orders'
