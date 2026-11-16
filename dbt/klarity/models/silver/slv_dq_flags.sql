-- Problems that do NOT remove the row from Silver, but must be visible.
select 'orders' as source_table, order_id as record_key, 'missing_estimated_date' as flag
from {{ ref('slv_orders') }} where estimated_delivery_at is null
union all
select 'orders', o.order_id, 'order_without_items'
from {{ ref('slv_orders') }} o
where not exists (select 1 from {{ ref('slv_order_items') }} i where i.order_id = o.order_id)
union all
select 'order_items', i.order_id || '/' || i.order_item_id, 'unknown_product'
from {{ ref('slv_order_items') }} i
where not exists (select 1 from {{ ref('slv_products') }} p where p.product_id = i.product_id)
union all
select 'order_items', i.order_id || '/' || i.order_item_id, 'unknown_seller'
from {{ ref('slv_order_items') }} i
where not exists (select 1 from {{ ref('slv_sellers') }} s where s.seller_id = i.seller_id)
union all
select 'products', product_id, 'missing_category'
from {{ ref('slv_products') }} where category_name = 'unknown'
