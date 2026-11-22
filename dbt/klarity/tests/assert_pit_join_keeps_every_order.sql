-- The point-in-time join must neither drop nor duplicate an order.
select 'row count differs' as problem
where (select count(*) from {{ ref('int_order_customer_pit') }}) <> (select count(*) from {{ ref('slv_orders') }})
