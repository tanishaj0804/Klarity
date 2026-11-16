-- One row per customer_id (an id is created per ORDER; customer_unique_id is the real person).
select * from {{ ref('stg_customers') }}
