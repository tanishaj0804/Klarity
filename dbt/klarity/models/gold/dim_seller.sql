select seller_id, zip_code_prefix, city, state
from {{ ref('slv_sellers') }}
