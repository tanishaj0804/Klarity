-- Money must be the same in the item-level fact and the order-level fact.
select 'totals differ' as problem
where abs(
    (select coalesce(sum(item_total), 0) from {{ ref('fct_order_items') }})
  - (select coalesce(sum(order_value), 0) from {{ ref('fct_orders') }})
) > 0.01
