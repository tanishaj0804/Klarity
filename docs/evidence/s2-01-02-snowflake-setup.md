# S2-01 and S2-02: Snowflake setup and roles

Script: `infra/snowflake/s2_setup.sql` (run top to bottom in a Snowsight worksheet as ACCOUNTADMIN).

## S2-01 checks
Run each statement and paste the output (a screenshot link is fine).

```sql
SHOW WAREHOUSES;               -- FIVETRAN_WH and TRANSFORM_WH: size XSMALL, auto_suspend 60
SHOW RESOURCE MONITORS;        -- KLARITY_MONITOR: notify 50/80 percent, suspend 100 percent
SHOW DATABASES;                -- BRONZE, SILVER, GOLD
```
Output:
```
COMPUTE_WH
FIVETRAN_WH
SNOWFLAKE_LEARNING_WH
SYSTEM$STREAMLIT_NOTEBOOK_WH
TRANSFORM_WH

KLARITY_MONITOR

BRONZE
GOLD
SILVER
SNOWFLAKE
SNOWFLAKE_LEARNING_DB
SNOWFLAKE_SAMPLE_DATA
USER$TANISHA
```

## S2-02 proof: one allowed and one refused statement per role
```sql
SHOW GRANTS TO ROLE LOADER;
SHOW GRANTS TO ROLE TRANSFORMER;
SHOW GRANTS TO ROLE REPORTER;
```

| Role | Allowed (should work) | Refused (should fail) | Result |
| --- | --- | --- | --- |
| LOADER | `USE ROLE LOADER; CREATE SCHEMA BRONZE.PROOF_TMP; DROP SCHEMA BRONZE.PROOF_TMP;` | `USE ROLE LOADER; SELECT * FROM SILVER.CORE.SLV_ORDERS LIMIT 1;` | invalid date |
| TRANSFORMER | `USE ROLE TRANSFORMER; SELECT COUNT(*) FROM SILVER.CORE.SLV_ORDERS;` | `USE ROLE TRANSFORMER; CREATE TABLE BRONZE.PROOF_TMP_T (a INT);` | Schema is not authorized |
| REPORTER | `USE ROLE REPORTER; SELECT 1;` (after Gold exists: `SELECT * FROM GOLD.MART.<table> LIMIT 1`) | `USE ROLE REPORTER; SELECT * FROM SILVER.CORE.SLV_ORDERS LIMIT 1;` | invalid date |

Note: dbt already runs as TRANSFORMER and builds SILVER.CORE (60 of 60 passed), which is live proof of the TRANSFORMER grants.
