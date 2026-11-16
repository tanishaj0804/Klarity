"""Snowflake connection helper (key-pair login). Used by the reconciliation script and by the
fallback Oracle loader. Settings come from the same .env file as the databases.

Settings (put them in .env, never in Git):
    SNOWFLAKE_ACCOUNT              e.g. ABCDEFG-XY12345   (the part before .snowflakecomputing.com)
    SNOWFLAKE_USER                 DBT_USER
    SNOWFLAKE_PRIVATE_KEY_PATH     C:\\Users\\you\\.snowflake_keys\\dbt_user.p8
    SNOWFLAKE_ROLE                 TRANSFORMER
    SNOWFLAKE_WAREHOUSE            TRANSFORM_WH
"""
import os

import klarity_db  # noqa: F401  (loads the .env file selected by KLARITY_ENV_FILE)

# Where Fivetran writes each source (schema prefix + source schema, see the instructions).
BRONZE_SCHEMA = {
    "oracle": os.environ.get("BRONZE_SCHEMA_ORACLE", "ORACLE_KLARITY_APP"),
    "mysql": os.environ.get("BRONZE_SCHEMA_MYSQL", "MYSQL_CRM"),
    "postgres": os.environ.get("BRONZE_SCHEMA_POSTGRES", "PG_PUBLIC"),
}


def setting(name, default=None, required=True):
    value = os.environ.get(name, default)
    if required and not value:
        raise SystemExit(f"Missing setting {name}. Add it to your .env file (see docs).")
    return value


def connect(database="BRONZE", schema=None):
    import snowflake.connector
    from cryptography.hazmat.primitives import serialization

    with open(setting("SNOWFLAKE_PRIVATE_KEY_PATH"), "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    der = key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
    return snowflake.connector.connect(
        account=setting("SNOWFLAKE_ACCOUNT"), user=setting("SNOWFLAKE_USER"), private_key=der,
        role=setting("SNOWFLAKE_ROLE", "TRANSFORMER"), warehouse=setting("SNOWFLAKE_WAREHOUSE", "TRANSFORM_WH"),
        database=database, schema=schema)
