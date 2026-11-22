{# Generic test, attached to the LATER timestamp column: it must not be before the `earlier` column.
   Nulls are allowed. Usage:
     - name: delivered_at
       tests:
         - valid_timeline: {arguments: {earlier: purchased_at}} #}
{% test valid_timeline(model, column_name, earlier) %}
select * from {{ model }}
where {{ earlier }} is not null and {{ column_name }} is not null and {{ column_name }} < {{ earlier }}
{% endtest %}
