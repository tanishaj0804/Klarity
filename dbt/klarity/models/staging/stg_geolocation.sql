{{ config(enabled=var('use_geolocation')) }}
select
    geolocation_id,
    lpad(trim(geolocation_zip_code_prefix), 5, '0')  as zip_code_prefix,
    geolocation_lat::float                           as lat,
    geolocation_lng::float                           as lng,
    initcap(trim(geolocation_city))                  as city,
    upper(trim(geolocation_state))                   as state
from {{ source('postgres', 'geolocation') }}
where coalesce(_fivetran_deleted, false) = false
