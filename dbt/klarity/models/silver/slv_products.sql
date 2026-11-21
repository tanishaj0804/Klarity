-- Fixes: missing category becomes 'unknown', English name added, weight 0 treated as missing.
select
    p.product_id,
    coalesce(p.category_name, 'unknown')                            as category_name,
    coalesce(t.category_name_english, p.category_name, 'unknown')   as category_name_english,
    p.name_length,
    p.description_length,
    p.photos_qty,
    nullif(p.weight_g, 0)  as weight_g,
    p.length_cm,
    p.height_cm,
    p.width_cm
from {{ ref('stg_products') }} p
left join {{ ref('stg_category_translation') }} t on t.category_name = p.category_name
