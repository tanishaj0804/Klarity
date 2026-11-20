{{ config(enabled=var('use_geolocation')) }}
-- One row per zip prefix: average position, most frequent city and state.
with counted as (
    select zip_code_prefix, city, state, count(*) as n
    from {{ ref('stg_geolocation') }}
    group by 1, 2, 3
),
top_city as (
    select zip_code_prefix, city, state
    from counted
    qualify row_number() over (partition by zip_code_prefix order by n desc, city) = 1
),
position as (
    select zip_code_prefix, avg(lat) as lat, avg(lng) as lng, count(*) as points
    from {{ ref('stg_geolocation') }}
    group by 1
)
select p.zip_code_prefix, p.lat, p.lng, p.points, t.city, t.state
from position p join top_city t using (zip_code_prefix)
