select r.*
from {{ ref('stg_order_reviews') }} r
where not exists (select 1 from {{ ref('rej_reviews') }} q where q.record_key = r.review_pk::varchar)
