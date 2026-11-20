select
    lower(trim(product_category_name))          as category_name,
    lower(trim(product_category_name_english))  as category_name_english
from {{ source('postgres', 'category_translation') }}
where coalesce(_fivetran_deleted, false) = false
