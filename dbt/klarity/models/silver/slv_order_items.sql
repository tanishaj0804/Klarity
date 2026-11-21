select i.*
from {{ ref('stg_order_items') }} i
where not exists (select 1 from {{ ref('rej_order_items') }} r where r.record_key = i.order_id || '/' || i.order_item_id)
