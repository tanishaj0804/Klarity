select i.order_id || '/' || i.order_item_id as record_key, 'invalid_price' as reason_code
from {{ ref('stg_order_items') }} i
where i.price is null or i.price < 0

union all

select i.order_id || '/' || i.order_item_id, 'order_not_in_silver'
from {{ ref('stg_order_items') }} i
where not exists (select 1 from {{ ref('slv_orders') }} o where o.order_id = i.order_id)
