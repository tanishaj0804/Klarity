# Architecture

Oracle, MySQL and PostgreSQL (AWS) -> Fivetran -> Snowflake (Bronze -> Silver -> Gold) -> dashboard.
Airflow on EC2 triggers Fivetran, then runs `dbt build` and `dbt test`.

| Layer | Built by | Rule |
| --- | --- | --- |
| Bronze | Fivetran | Exact copy of sources. Never edited by hand. |
| Silver | dbt (`stg_` models) | Typed, deduplicated, standardised. One row per business key. |
| Gold | dbt (marts) | Star schema and KPI tables. The only layer dashboards read. |

See the diagram in the README. Decisions are recorded in `docs/adr/`.
