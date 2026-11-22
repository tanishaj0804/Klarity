{# SCD Type 2: every time a customer's address changes, dbt closes the old row and opens a new one.
   Target database and schema come from dbt_project.yml (GOLD.MART). Run it with: dbt snapshot #}
{% snapshot snap_customers %}
{{
    config(
        unique_key='customer_id',
        strategy='check',
        check_cols=['city', 'state', 'zip_code_prefix']
    )
}}
select customer_id, customer_unique_id, zip_code_prefix, city, state
from {{ ref('slv_customers') }}
{% endsnapshot %}
