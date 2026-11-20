select
    seller_id,
    lpad(trim(seller_zip_code_prefix), 5, '0')  as zip_code_prefix,
    initcap(trim(seller_city))                  as city,
    upper(trim(seller_state))                   as state
from {{ source('postgres', 'sellers') }}
where coalesce(_fivetran_deleted, false) = false
