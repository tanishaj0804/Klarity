"""Reconcile the source databases with Bronze in Snowflake (story S2-08).

    python scripts/reconcile_bronze.py --skip geolocation --out docs/evidence/s2-08-bronze-reconciliation.md

For each table it compares the source database with Bronze on: row count, distinct keys,
sums and null counts (the same checks as verify_load.py, now across systems). Bronze rows
that Fivetran marked as deleted (_FIVETRAN_DELETED = TRUE) are not counted, because the
source no longer has them. Exit code 1 if any check fails.

Run it right after a sync finishes, with no source changes in between.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sources"))

from klarity_db import SYSTEM_OF, get_engine  # noqa: E402
from verify_load import SPECS, db_side, same  # noqa: E402

KINDS = ("rows", "distinct", "sum", "nulls")   # min/max dates differ in type between systems, skipped

    
def bronze_sql(schema, table, kind, column):
    if schema == "MYSQL_CRM":
        src = f'BRONZE.{schema}."{table}"'
        col = f'"{column}"' if column else None
        live = 'COALESCE("_fivetran_deleted", FALSE) = FALSE'

    else:
        src = f"BRONZE.{schema}.{table.upper()}"
        col = column.upper() if column else None
        live = "COALESCE(_FIVETRAN_DELETED, FALSE) = FALSE"

    if kind == "rows":
        return f"SELECT COUNT(*) FROM {src} WHERE {live}"
    if kind == "distinct":
        return f"SELECT COUNT(DISTINCT {col}) FROM {src} WHERE {live}"
    if kind == "sum":
        return f"SELECT COALESCE(SUM({col}), 0) FROM {src} WHERE {live}"
    if kind == "nulls":
        return f"SELECT COUNT(*) FROM {src} WHERE {live} AND {col} IS NULL"
    raise ValueError(kind)



def reconcile(source_value, bronze_value, schemas, skip=()):
    """source_value(table, kind, column) and bronze_value(sql) are passed in so the logic can be tested."""
    results = []
    for table, kind, column in SPECS:
        if kind not in KINDS or table in skip:
            continue
        s = source_value(table, kind, column)
        b = bronze_value(bronze_sql(schemas[SYSTEM_OF[table]], table, kind, column))
        label = kind + (f" {column}" if column else "")
        results.append((SYSTEM_OF[table], table, label, s, b, same(s, b)))
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--skip", nargs="*", default=[], help="tables not synced, for example geolocation")
    ap.add_argument("--out", help="write a markdown table to this file (UTF-8)")
    args = ap.parse_args(argv)

    from klarity_snowflake import BRONZE_SCHEMA, connect
    engines = {s: get_engine(s) for s in ("oracle", "mysql", "postgres")}
    conn = connect()
    cur = conn.cursor()

    def bronze_value(sql):
        cur.execute(sql)
        return cur.fetchone()[0]

    results = reconcile(lambda t, k, c: db_side(engines, t, k, c), bronze_value, BRONZE_SCHEMA, set(args.skip))
    conn.close()

    rows = [("system", "table", "check", "source", "bronze", "result")]
    rows += [(a, b, c, str(d), str(e), "PASS" if ok else "FAIL") for a, b, c, d, e, ok in results]
    widths = [max(len(r[i]) for r in rows) for i in range(6)]
    lines = ["| " + " | ".join(v.ljust(w) for v, w in zip(r, widths)) + " |" for r in rows]
    lines.insert(1, "|" + "|".join("-" * (w + 2) for w in widths) + "|")
    failed = sum(1 for r in results if not r[5])
    summary = f"\n{len(results) - failed} passed, {failed} failed"
    print("\n".join(lines) + summary)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text("\n".join(lines) + "\n" + summary + "\n", encoding="utf-8", newline="\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
