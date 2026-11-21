# ADR 0006: Oracle ingestion without Fivetran

Status: approved

Date: 18 Nov 2026

## Context

The project attempted to onboard Oracle XE as a source using the Fivetran Oracle connector.

The Oracle connector was configured with:

- SSH tunnel
- Host: 127.0.0.1
- Port: 1521
- Service: XEPDB1
- User: klarity_ro

Connectivity was successfully verified:

- SSH tunnel connection succeeded
- Oracle service XEPDB1 was reachable
- User authentication succeeded
- Oracle tables could be accessed through the read-only account

During validation, Fivetran failed while checking Oracle system views and returned errors indicating insufficient access to views such as:

- SYS.V_$DATABASE
- SYS.V_$ARCHIVED_LOG
- SYS.V_$TRANSACTION
- SYS.V_$PARAMETER
- SYS.V_$PDBS

These views are required for Oracle change-data-capture and log-based replication validation.

Oracle XE and the project's read-only account do not provide the access level required by the Fivetran Oracle connector without additional database administration and logging configuration.

## Decision

Use a Python ingestion process (sources/load_oracle_to_snowflake.py) instead of the Fivetran Oracle connector.

The loader copies:

- orders
- order_items
- order_payments

into:

BRONZE.ORACLE_KLARITY_APP

using a full refresh strategy.

## Consequences

Advantages:

- Works with Oracle XE
- Does not consume Fivetran MAR usage
- Simpler operational setup
- Compatible with the project environment

Limitations:

- No log-based CDC
- Updates and deletes are captured only during full refreshes
- Airflow will execute the refresh job in Sprint 4
- Numeric reconciliation uses a tolerance of 0.01 for monetary values
