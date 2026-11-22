-- Point-in-time join: for every order, the customer version that was in force when it was bought.
-- A plain join on customer_id would show the customer's CURRENT address on old orders.
-- The ranges of one customer never overlap, so this returns exactly one row per order.
select
    o.order_id,
    c.customer_sk,
    c.customer_unique_id,
    c.city   as customer_city_at_purchase,
    c.state  as customer_state_at_purchase
from {{ ref('slv_orders') }} as o
left join {{ ref('dim_customer') }} as c
    on  c.customer_id = o.customer_id
    and o.purchased_at >= c.effective_from
    and o.purchased_at <  c.effective_to
