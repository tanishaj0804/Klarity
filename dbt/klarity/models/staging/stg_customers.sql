-- Text clean-up happens here: the simulator injects CAPITAL cities and lowercase states.
-- Zip prefixes lost their leading zeros in the CSV, so they are padded back to 5 digits.
select
    "customer_id"                                       as customer_id,
    "customer_unique_id"                                as customer_unique_id,
    lpad(trim("customer_zip_code_prefix"), 5, '0')      as zip_code_prefix,
    initcap(trim("customer_city"))                      as city,
    upper(trim("customer_state"))                       as state
from {{ source('mysql', 'customers') }}
where coalesce("_fivetran_deleted", false) = false