-- Reviews rejected from Silver. record_key is the surrogate key review_pk (review_id repeats in the source).
select r.review_pk::varchar as record_key, 'invalid_score' as reason_code
from {{ ref('stg_order_reviews') }} r
where r.review_score is null or r.review_score not between 1 and 5

union all

-- The order was deleted at the source, or was itself rejected.
select r.review_pk::varchar, 'order_not_in_silver'
from {{ ref('stg_order_reviews') }} r
where not exists (select 1 from {{ ref('slv_orders') }} o where o.order_id = r.order_id)

union all

-- The same review stored twice for the same order: keep the newest, reject the rest.
select review_pk::varchar, 'duplicate_review'
from (
    select review_pk,
           row_number() over (partition by review_id, order_id
                              order by review_answered_at desc nulls last, review_pk desc) as rn
    from {{ ref('stg_order_reviews') }}
)
where rn > 1
