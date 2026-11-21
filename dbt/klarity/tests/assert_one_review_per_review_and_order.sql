select review_id, order_id, count(*) as copies
from {{ ref('slv_reviews') }}
group by 1, 2
having count(*) > 1
