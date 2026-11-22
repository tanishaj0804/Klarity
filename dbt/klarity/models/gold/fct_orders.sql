-- Grain: one row per order. Payments are pivoted into one column per payment type (Jinja loop),
-- the latest review is kept per order, and the customer is the one in force at purchase.
with payments as (
    select
        order_id,
        count(*)                as payment_count,
        sum(payment_value)      as payment_total,
        {{ pivot_sum('payment_type', 'payment_value', var('payment_types'), prefix='paid_') }}
    from {{ ref('slv_order_payments') }}
    group by order_id
),
items as (
    select
        order_id,
        count(*)                       as item_count,
        count(distinct seller_id)      as seller_count,
        sum(price)                     as items_value,
        sum(freight_value)             as freight_value
    from {{ ref('slv_order_items') }}
    group by order_id
),
latest_review as (
    select order_id, review_score
    from {{ ref('slv_reviews') }}
    qualify row_number() over (partition by order_id order by review_created_at desc, review_pk desc) = 1
)
select
    o.order_id,
    p.customer_sk,
    p.customer_unique_id,
    p.customer_city_at_purchase,
    p.customer_state_at_purchase,
    o.order_status,
    cast(o.purchased_at as date)                                  as purchase_date,
    o.purchased_at,
    o.delivered_at,
    o.estimated_delivery_at,
    coalesce(i.item_count, 0)                                     as item_count,
    coalesce(i.seller_count, 0)                                   as seller_count,
    coalesce(i.items_value, 0)                                    as items_value,
    coalesce(i.freight_value, 0)                                  as freight_value,
    coalesce(i.items_value, 0) + coalesce(i.freight_value, 0)     as order_value,
    coalesce(pay.payment_count, 0)                                as payment_count,
    coalesce(pay.payment_total, 0)                                as payment_total,
    {%- for t in var('payment_types') %}
    coalesce(pay.paid_{{ t }}, 0)                                 as paid_{{ t }},
    {%- endfor %}
    datediff('hour', o.purchased_at, o.approved_at)               as hours_to_approval,
    datediff('hour', o.approved_at, o.delivered_to_carrier_at)    as hours_to_carrier,
    datediff('hour', o.delivered_to_carrier_at, o.delivered_at)   as hours_in_transit,
    o.delivery_days,
    o.is_late,
    case when o.is_late then datediff('day', o.estimated_delivery_at, o.delivered_at) else 0 end as days_late,
    r.review_score
from {{ ref('slv_orders') }} as o
left join {{ ref('int_order_customer_pit') }} as p on p.order_id = o.order_id
left join items as i on i.order_id = o.order_id
left join payments as pay on pay.order_id = o.order_id
left join latest_review as r on r.order_id = o.order_id
