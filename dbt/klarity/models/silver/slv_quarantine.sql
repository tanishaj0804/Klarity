-- Every row kept out of Silver, with the table it came from and why.
-- The Data Health page and the dbt tests read this table.
select 'orders' as source_table, record_key, reason_code, current_timestamp() as detected_at from {{ ref('rej_orders') }}
union all
select 'order_items', record_key, reason_code, current_timestamp() from {{ ref('rej_order_items') }}
union all
select 'order_payments', record_key, reason_code, current_timestamp() from {{ ref('rej_order_payments') }}
union all
select 'order_reviews', record_key, reason_code, current_timestamp() from {{ ref('rej_reviews') }}
