{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key=['order_id', 'order_item_id'],
        on_schema_change='append_new_columns',
        post_hook="{{ delete_missing_rows(ref('slv_order_items'), ['order_id', 'order_item_id']) }}"
    )
}}
-- Grain: one row per order item. Loaded incrementally with MERGE.
-- Which rows are reloaded on every run:
--   1. orders purchased in the last N days (var reprocess_days, default 30): late status changes,
--   2. orders that are still open (not delivered / canceled / unavailable): they will still change.
-- Rows that disappear from Silver are removed by the post-hook (see macros/delete_missing_rows.sql).
-- Full rebuild: dbt build --full-refresh --select fct_order_items
select
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    p.customer_sk,
    cast(o.purchased_at as date)        as purchase_date,
    o.purchased_at,
    o.order_status,
    i.price,
    i.freight_value,
    i.price + i.freight_value           as item_total,
    o.delivery_days,
    o.is_late,
    current_timestamp                   as loaded_at
from {{ ref('slv_order_items') }} as i
join {{ ref('slv_orders') }} as o on o.order_id = i.order_id
left join {{ ref('int_order_customer_pit') }} as p on p.order_id = i.order_id
{% if is_incremental() %}
where o.purchased_at >= (select max(purchased_at) from {{ this }}) - interval '{{ var("reprocess_days", 30) }} days'
   or o.order_status not in ('delivered', 'canceled', 'unavailable')
{% endif %}
