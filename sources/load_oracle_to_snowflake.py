"""FALLBACK: copy the Oracle tables into Snowflake Bronze without Fivetran.

Use this only if Fivetran's Oracle connector is not available on your plan or does not work
with Oracle XE. It needs a short ADR and your mentor's approval (it replaces a tool the
architecture names). It is a FULL REFRESH: each run replaces the table, so deletes and
changes are picked up, but it is not log-based change capture.

    python sources/load_oracle_to_snowflake.py              # orders, order_items, order_payments
    python sources/load_oracle_to_snowflake.py --tables orders

It writes to BRONZE.<BRONZE_SCHEMA_ORACLE> with the same table names Fivetran would use, plus
the two Fivetran columns (_FIVETRAN_DELETED = FALSE, _FIVETRAN_SYNCED), so the dbt models and the
reconciliation script work unchanged. Money columns are written as floating point (written with
two decimals); the reconciliation tolerance is 0.01.
"""
import argparse
import sys
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select

from klarity_db import LOAD_ORDER, T, describe_targets, get_engine

CHUNK = 50_000


def read_table(engine, table):
    """Yield the table as DataFrames with UPPERCASE column names and Fivetran's two columns."""
    columns = list(T[table].columns)
    with engine.connect() as conn:
        result = conn.execution_options(stream_results=True).execute(select(*columns))
        while True:
            rows = result.fetchmany(CHUNK)
            if not rows:
                break
            frame = pd.DataFrame(rows, columns=[c.name.upper() for c in columns])
            for col in columns:
                if col.type.__class__.__name__ == "Numeric":
                    frame[col.name.upper()] = frame[col.name.upper()].astype(float)
            frame["_FIVETRAN_DELETED"] = False
            frame["_FIVETRAN_SYNCED"] = datetime.now(timezone.utc).replace(tzinfo=None)
            yield frame


def load_table(conn, engine, table, schema):
    from snowflake.connector.pandas_tools import write_pandas
    first = True
    total = 0
    for frame in read_table(engine, table):
        ok, _, rows, _ = write_pandas(conn, frame, table.upper(), database="BRONZE", schema=schema,
                                      auto_create_table=first, overwrite=first, quote_identifiers=True)
        if not ok:
            raise SystemExit(f"write_pandas failed for {table}")
        first = False
        total += rows
    if first:   # empty source table: still create it so dbt does not fail
        raise SystemExit(f"{table} is empty in Oracle. Load the source first (load_olist.py).")
    return total


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--tables", nargs="*", default=LOAD_ORDER["oracle"])
    args = ap.parse_args(argv)
    print(describe_targets(["oracle"]))

    from klarity_snowflake import BRONZE_SCHEMA, connect
    schema = BRONZE_SCHEMA["oracle"]
    conn = connect(database="BRONZE")
    conn.cursor().execute(f'CREATE SCHEMA IF NOT EXISTS BRONZE."{schema}"')
    engine = get_engine("oracle")
    for table in args.tables:
        n = load_table(conn, engine, table, schema)
        print(f"{table}: {n} rows written to BRONZE.{schema}.{table.upper()}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
