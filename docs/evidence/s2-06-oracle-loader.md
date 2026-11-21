# S2-06: Oracle to Snowflake Bronze (fallback decision)

- Day-1 check done: Fivetran's Oracle connector fails on Oracle XE with the read-only user
  (missing access to SYS.V_$DATABASE, V_$ARCHIVED_LOG and others). Details: `docs/adr/0006-oracle-injestion-fallback.md` (status: approved, 20 Nov 2026).
- Loader: `sources/load_oracle_to_snowflake.py` -> `BRONZE.ORACLE_KLARITY_APP` (orders, order_items, order_payments), full refresh.
- Bronze row counts equal the source (99834 orders, 113402 order_items, 104265 order_payments),
  see `docs/evidence/s2-08-bronze-reconciliation.md`.
