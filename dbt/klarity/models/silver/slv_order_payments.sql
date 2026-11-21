select p.*
from {{ ref('stg_order_payments') }} p
where not exists (select 1 from {{ ref('rej_order_payments') }} r where r.record_key = p.order_id || '/' || p.payment_sequential)
