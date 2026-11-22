-- The pivoted payment columns must add up to the payment total. A difference means a payment type
-- exists in the data that is missing from var payment_types in dbt_project.yml.
select order_id, payment_total,
       {% for t in var('payment_types') %}paid_{{ t }}{{ " + " if not loop.last }}{% endfor %} as pivot_sum
from {{ ref('fct_orders') }}
where abs(payment_total - ({% for t in var('payment_types') %}paid_{{ t }}{{ " + " if not loop.last }}{% endfor %})) > 0.005
