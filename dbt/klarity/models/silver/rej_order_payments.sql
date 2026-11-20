select p.order_id || '/' || p.payment_sequential as record_key, 'invalid_payment_value' as reason_code
from {{ ref('stg_order_payments') }} p
where p.payment_value is null or p.payment_value < 0

union all

select p.order_id || '/' || p.payment_sequential, 'order_not_in_silver'
from {{ ref('stg_order_payments') }} p
where not exists (select 1 from {{ ref('slv_orders') }} o where o.order_id = p.order_id)
