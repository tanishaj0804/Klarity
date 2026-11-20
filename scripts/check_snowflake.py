"""Check that your Snowflake login works and show what Bronze contains.

    python scripts/check_snowflake.py             # who am I, what role, which schemas and tables are in BRONZE
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sources"))

from klarity_snowflake import connect  # noqa: E402


def main():
    conn = connect(database="BRONZE")
    cur = conn.cursor()
    cur.execute("select current_user(), current_role(), current_warehouse()")
    print("Logged in as: user=%s role=%s warehouse=%s" % cur.fetchone())
    cur.execute("show schemas in database BRONZE")
    schemas = [r[1] for r in cur.fetchall() if r[1] not in ("INFORMATION_SCHEMA", "PUBLIC")]
    print("Schemas in BRONZE:", ", ".join(schemas) or "(none yet)")
    for schema in schemas:
        cur.execute(f"select table_name, row_count from BRONZE.information_schema.tables "
                    f"where table_schema = '{schema}' and table_type = 'BASE TABLE' order by 1")
        for name, rows in cur.fetchall():
            print(f"  {schema}.{name}: {rows if rows is not None else '?'} rows")
    conn.close()


if __name__ == "__main__":
    main()
