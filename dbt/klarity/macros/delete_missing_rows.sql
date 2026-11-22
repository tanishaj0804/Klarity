{# Delete handling for incremental models. Silver is rebuilt from Bronze every run, so a row that
   was deleted (or quarantined) upstream disappears from Silver. An incremental model never removes
   rows by itself, so this post-hook deletes every row whose key no longer exists in the source.
   Use as: post_hook="{{ delete_missing_rows(ref('slv_order_items'), ['order_id', 'order_item_id']) }}" #}
{% macro delete_missing_rows(source_relation, keys) -%}
delete from {{ this }}
where ({{ keys | join(', ') }}) not in (select {{ keys | join(', ') }} from {{ source_relation }})
{%- endmacro %}
