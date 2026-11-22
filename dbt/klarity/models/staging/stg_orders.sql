
-- Staging: rename and type columns.
-- Oracle timestamps arrive in Bronze as Unix microseconds.
-- Convert them to Snowflake timestamps.
-- Rows marked as deleted by Fivetran are dropped here.

select
    order_id,
    customer_id,
    lower(trim(order_status)) as order_status,

    to_timestamp_ntz(order_purchase_timestamp / 1000000) as purchased_at,
    to_timestamp_ntz(order_approved_at / 1000000) as approved_at,
    to_timestamp_ntz(order_delivered_carrier_date / 1000000) as delivered_to_carrier_at,
    to_timestamp_ntz(order_delivered_customer_date / 1000000) as delivered_at,
    to_timestamp_ntz(order_estimated_delivery_date / 1000000) as estimated_delivery_at

from {{ source('oracle', 'orders') }}
where coalesce(_fivetran_deleted, false) = false
