select
    order_id,
    payment_sequential::int           as payment_sequential,
    lower(trim(payment_type))         as payment_type,
    payment_installments::int         as payment_installments,
    payment_value::number(10, 2)      as payment_value
from {{ source('oracle', 'order_payments') }}
where coalesce(_fivetran_deleted, false) = false
