-- Reconciliation inside Silver: orders staged = orders kept + distinct orders rejected.
with staged as (select count(*) as n from {{ ref('stg_orders') }}),
     kept as (select count(*) as n from {{ ref('slv_orders') }}),
     rejected as (select count(distinct record_key) as n from {{ ref('slv_quarantine') }} where source_table = 'orders')
select staged.n as staged, kept.n as kept, rejected.n as rejected
from staged, kept, rejected
where staged.n <> kept.n + rejected.n
