-- The source columns are spelled "lenght". They are renamed here, not at the source.
select
    product_id,
    lower(trim(product_category_name))  as category_name,
    product_name_lenght::int            as name_length,
    product_description_lenght::int     as description_length,
    product_photos_qty::int             as photos_qty,
    product_weight_g::int               as weight_g,
    product_length_cm::int              as length_cm,
    product_height_cm::int              as height_cm,
    product_width_cm::int               as width_cm
from {{ source('postgres', 'products') }}
where coalesce(_fivetran_deleted, false) = false
