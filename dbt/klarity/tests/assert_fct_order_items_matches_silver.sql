-- After every incremental run the fact must hold exactly the order items that exist in Silver:
-- nothing missing (not loaded) and nothing extra (deleted or quarantined upstream, not removed).
select 'in silver, missing in fact' as problem, order_id, order_item_id
from {{ ref('slv_order_items') }} s
where not exists (select 1 from {{ ref('fct_order_items') }} f
                  where f.order_id = s.order_id and f.order_item_id = s.order_item_id)
union all
select 'in fact, not in silver', order_id, order_item_id
from {{ ref('fct_order_items') }} f
where not exists (select 1 from {{ ref('slv_order_items') }} s
                  where f.order_id = s.order_id and f.order_item_id = s.order_item_id)
