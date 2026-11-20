select * from {{ ref('slv_orders') }} where delivered_at < purchased_at
