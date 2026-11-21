-- Oracle XE (service XEPDB1): read-only user (story S2-03).
-- Used by the fallback loader (sources/load_oracle_to_snowflake.py) and by Fivetran if its
-- Oracle connector is available on your plan (Fivetran needs more: ARCHIVELOG and LogMiner
-- settings, see its Oracle setup guide).
-- Run as the app user's owner or SYSTEM:
--   sudo docker exec -i klarity-oracle sh -c 'sqlplus -s system/"$ORACLE_PASSWORD"@//localhost:1521/XEPDB1' < oracle_readonly.sql

CREATE USER klarity_ro IDENTIFIED BY "CHANGE_ME_Strong1";
GRANT CREATE SESSION TO klarity_ro;
GRANT SELECT ON klarity_app.orders TO klarity_ro;
GRANT SELECT ON klarity_app.order_items TO klarity_ro;
GRANT SELECT ON klarity_app.order_payments TO klarity_ro;
-- Proof: connect as klarity_ro, SELECT works, INSERT gives ORA-01031 insufficient privileges.
EXIT;
