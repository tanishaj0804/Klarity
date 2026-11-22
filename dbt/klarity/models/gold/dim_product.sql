select
    product_id,
    category_name,
    category_name_english,
    name_length,
    description_length,
    photos_qty,
    weight_g,
    length_cm * height_cm * width_cm as volume_cm3
from {{ ref('slv_products') }}
