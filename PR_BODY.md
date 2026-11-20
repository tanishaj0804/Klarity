## What and why

Sprint 2 delivery: Bronze is loaded from all three sources and verified, and the Silver layer is built in dbt.

- Snowflake: warehouses, resource monitor, databases and roles (`infra/snowflake/s2_setup.sql`)
- Read-only source users and Fivetran source prep (`infra/aws/source_prep/`)
- Fivetran: PostgreSQL and MySQL to Bronze
- Oracle to Bronze with a Python loader instead of Fivetran (ADR 0006, approved by the mentor)
- Reconciliation: 21 of 21 checks PASS (`docs/evidence/s2-08-bronze-reconciliation.md`)
- dbt Silver: 21 models, 39 tests, all passing; quarantine of 147 rows
- Cost log started

Closes #21, closes #22, closes #23, closes #24, closes #25, closes #26, closes #28, closes #31

Not closed on purpose: #27 (add firewall proof first), #29 (simulator to Bronze check), #30 (schema drift, cut).

## Checklist

- [x] Acceptance criteria met and demonstrated (evidence files under `docs/evidence/`)
- [x] Safe to re-run
- [x] Tests or checks pass (`dbt build` 60 of 60; CI)
- [x] Docs updated
- [x] No secrets or hard-coded paths
