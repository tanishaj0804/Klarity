select
    review_pk,
    review_id,
    order_id,
    review_score::int                       as review_score,
    review_comment_title                    as comment_title,
    review_comment_message                  as comment_message,
    review_creation_date::timestamp_ntz     as review_created_at,
    review_answer_timestamp::timestamp_ntz  as review_answered_at
from {{ source('mysql', 'order_reviews') }}
where coalesce(_fivetran_deleted, false) = false
