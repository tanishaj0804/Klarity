{# Builds one "sum(case when ...)" column per value in a list. Used to pivot payment types into columns.
   pivot_sum('payment_type', 'payment_value', ['credit_card', 'boleto'], prefix='paid_')
   -> sum(case when payment_type = 'credit_card' then payment_value else 0 end) as paid_credit_card, ... #}
{% macro pivot_sum(column, value, values, prefix='') -%}
{%- for v in values %}
    sum(case when {{ column }} = '{{ v }}' then {{ value }} else 0 end) as {{ prefix }}{{ v }}{{ "," if not loop.last }}
{%- endfor %}
{%- endmacro %}
