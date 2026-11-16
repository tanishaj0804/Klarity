-- PostgreSQL (database catalog): prepare for Fivetran (story S2-03 / S2-04).
-- Run as the admin user inside the postgres container:
--   sudo docker exec -i klarity-postgres psql -U <PG_USER from .env> -d catalog -v pw="'<new password>'" -f - < postgres_fivetran.sql
-- Re-runnable except the slot line (ignore "already exists").

-- 1. Read-only user for Fivetran
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'fivetran') THEN
    CREATE ROLE fivetran LOGIN;
  END IF;
END $$;
ALTER ROLE fivetran WITH PASSWORD :pw;
GRANT USAGE ON SCHEMA public TO fivetran;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO fivetran;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO fivetran;
ALTER ROLE fivetran WITH REPLICATION;

-- 2. Logical replication objects (wal_level=logical is already set by docker-compose)
DROP PUBLICATION IF EXISTS fivetran_pub;
CREATE PUBLICATION fivetran_pub FOR TABLE products, sellers, category_translation;
-- geolocation (1M rows) is left out on purpose to stay inside Fivetran's free row limit.
-- To add it later:  ALTER PUBLICATION fivetran_pub ADD TABLE geolocation;

SELECT pg_create_logical_replication_slot('fivetran_pgoutput_slot', 'pgoutput');

-- 3. Checks
SHOW wal_level;                                   -- must be: logical
SELECT * FROM pg_publication_tables;              -- 3 tables
SELECT slot_name, plugin, active FROM pg_replication_slots;
