-- SCD Type 2 customer dimension: one row per customer_id and address version.
-- effective_from / effective_to are the period in which that address was in force.
-- The first version is open to the past (1900) because it is the address the customer had
-- before we started watching. The last version is open to the future (9999).
select
    dbt_scd_id                                                                  as customer_sk,
    customer_id,
    customer_unique_id,
    zip_code_prefix,
    city,
    state,
    row_number() over (partition by customer_id order by dbt_valid_from)        as version_no,
    case when row_number() over (partition by customer_id order by dbt_valid_from) = 1
         then cast('1900-01-01' as timestamp) else dbt_valid_from end           as effective_from,
    coalesce(dbt_valid_to, cast('9999-12-31' as timestamp))                     as effective_to,
    dbt_valid_to is null                                                        as is_current
from {{ ref('snap_customers') }}
