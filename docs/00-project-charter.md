# Project charter

| | |
| --- | --- |
| Project | Klarity: Retail Analytics Platform |
| Client / sponsor | _mentor name_ |
| Delivery lead | Tanisha J |
| Duration | 8 weeks, 4 sprints (2 Nov - 25 Dec 2026) |

## Objective

Build one governed data platform that copies Oracle, MySQL and PostgreSQL data into
Snowflake, models it with dbt (Bronze / Silver / Gold), refreshes nightly with Airflow
and serves a dashboard.

## Scope

In: Olist data in three databases, Fivetran ingestion, Snowflake, dbt, Airflow, CI/CD,
one dashboard, handover documents.
Out: real-time streaming, machine learning, high availability, multi-region.

## Key risks

| Risk | Mitigation |
| --- | --- |
| Snowflake trial ends early | Create the account at Sprint 2, resource monitor, agree a fallback |
| Cloud cost overrun | Budget alerts, stop EC2 when idle, weekly billing check |
| Oracle connector difficult | Connect it last, leave buffer time |
| Secrets leaked to Git | .gitignore, detect-private-key hook, rotate if leaked |
| Fivetran free-tier limit | Track monthly active rows after each sync |
