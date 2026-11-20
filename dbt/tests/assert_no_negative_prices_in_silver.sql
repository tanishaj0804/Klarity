-- Returns rows when a negative price reached Silver (the test fails if any row is returned).
select * from {{ ref('slv_order_items') }} where price < 0
