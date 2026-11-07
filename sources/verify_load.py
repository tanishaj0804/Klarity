"""Prove the load is correct (story S1-09), and check simulator changes (story S1-10).

Baseline check, run right after load_olist.py and BEFORE daily_changes.py:
    python sources/verify_load.py
    python sources/verify_load.py --out docs/evidence/s1-09-load-verification.md

Change check, run after daily_changes.py:
    python sources/verify_load.py --changes logs/change_log.jsonl

For every table it compares the CSV file with what is in the database: row counts,
distinct keys, sums, min/max dates and null counts. It then checks the links between
databases (for example orders whose customer is missing from MySQL). Exit code 1 if
any check fails.
"""
import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import func, select

from klarity_db import CSV_OF, REPO, SYSTEM_OF, T, convert_values, get_engine

# (table, kind, column). kinds: rows, distinct, sum, min, max, nulls
SPECS = [
    ("orders", "rows", None), ("orders", "distinct", "order_id"),
    ("orders", "min", "order_purchase_timestamp"), ("orders", "max", "order_purchase_timestamp"),
    ("orders", "nulls", "order_approved_at"), ("orders", "nulls", "order_delivered_customer_date"),
    ("order_items", "rows", None), ("order_items", "sum", "price"),
    ("order_items", "sum", "freight_value"), ("order_items", "distinct", "product_id"),
    ("order_payments", "rows", None), ("order_payments", "sum", "payment_value"),
    ("customers", "rows", None), ("customers", "distinct", "customer_unique_id"),
    ("order_reviews", "rows", None), ("order_reviews", "distinct", "review_id"),
    ("order_reviews", "sum", "review_score"),
    ("products", "rows", None), ("products", "nulls", "product_category_name"),
    ("products", "sum", "product_weight_g"),
    ("sellers", "rows", None), ("sellers", "distinct", "seller_state"),
    ("category_translation", "rows", None),
    ("geolocation", "rows", None), ("geolocation", "distinct", "geolocation_zip_code_prefix"),
]


def csv_values(data_dir, table, column):
    values = []
    for chunk in pd.read_csv(data_dir / CSV_OF[table], dtype=str, keep_default_na=False,
                             encoding="utf-8", usecols=[column], chunksize=100_000):
        values.extend(chunk[column].tolist())
    return convert_values(values, T[table].c[column].type)


def csv_rows(data_dir, table):
    first = next(c.name for c in T[table].columns if c.name not in ("review_pk", "geolocation_id"))
    return len(csv_values(data_dir, table, first))


def csv_side(data_dir, table, kind, column):
    if kind == "rows":
        return csv_rows(data_dir, table)
    vals = csv_values(data_dir, table, column)
    present = [v for v in vals if v is not None]
    return {"distinct": lambda: len(set(present)), "sum": lambda: sum(present),
            "min": lambda: min(present), "max": lambda: max(present),
            "nulls": lambda: len(vals) - len(present)}[kind]()


def db_side(engines, table, kind, column):
    t = T[table]
    eng = engines[SYSTEM_OF[table]]
    if kind == "rows":
        stmt = select(func.count()).select_from(t)
    elif kind == "distinct":
        stmt = select(func.count(t.c[column].distinct()))
    elif kind == "nulls":
        stmt = select(func.count()).select_from(t).where(t.c[column].is_(None))
    else:
        stmt = select(getattr(func, kind)(t.c[column]))
    with eng.connect() as conn:
        value = conn.execute(stmt).scalar_one()
    return 0 if value is None and kind in ("sum", "nulls", "rows", "distinct") else value


def same(a, b):
    if isinstance(a, (int, float, Decimal)) and isinstance(b, (int, float, Decimal)):
        return abs(float(a) - float(b)) <= 0.01
    return a == b


def db_ids(engines, table, column):
    with engines[SYSTEM_OF[table]].connect() as conn:
        return {r[0] for r in conn.execute(select(T[table].c[column]))}


def baseline(args, engines):
    data_dir = Path(args.data_dir)
    results = []
    for table, kind, column in SPECS:
        label = f"{kind}" + (f" {column}" if column else "")
        csv_v, db_v = csv_side(data_dir, table, kind, column), db_side(engines, table, kind, column)
        results.append((SYSTEM_OF[table], table, label, csv_v, db_v, same(csv_v, db_v)))

    # Links between databases: orphan counts must be the same in the CSV and in the databases.
    links = [("orders", "customer_id", "customers", "customer_id"),
             ("order_items", "product_id", "products", "product_id"),
             ("order_items", "seller_id", "sellers", "seller_id"),
             ("order_reviews", "order_id", "orders", "order_id"),
             ("products", "product_category_name", "category_translation", "product_category_name")]
    for child, ccol, parent, pcol in links:
        parent_csv = set(csv_values(data_dir, parent, pcol))
        child_csv = csv_values(data_dir, child, ccol)
        csv_orphans = sum(1 for v in child_csv if v is not None and v not in parent_csv)
        parent_db = db_ids(engines, parent, pcol)
        with engines[SYSTEM_OF[child]].connect() as conn:
            child_db = [r[0] for r in conn.execute(select(T[child].c[ccol]))]
        db_orphans = sum(1 for v in child_db if v is not None and v not in parent_db)
        results.append((f"{SYSTEM_OF[child]}->{SYSTEM_OF[parent]}", child,
                        f"orphans {ccol} not in {parent}", csv_orphans, db_orphans,
                        csv_orphans == db_orphans))
    return results


def changes(args, engines):
    """Check every entry of the change log against the databases."""
    entries = [json.loads(line) for line in Path(args.changes).read_text().splitlines() if line.strip()]
    deleted_orders = {e["key"]["order_id"] for e in entries if e["type"] == "deleted_order"}
    deleted_review_ids = {e["detail"]["review_id"] for e in entries if e["type"] == "deleted_review"}
    final_status, final_customer = {}, {}
    for e in entries:  # last write wins
        if e["type"] == "status_update":
            final_status[e["key"]["order_id"]] = e["detail"]["new_status"]
        if e["type"] in ("mixed_case", "address_change"):
            final_customer[e["key"]["customer_id"]] = (e["detail"]["city"], e["detail"]["state"])

    ora, my = engines["oracle"], engines["mysql"]
    o, i, p, c, r = T["orders"], T["order_items"], T["order_payments"], T["customers"], T["order_reviews"]

    def one(eng, stmt):
        with eng.connect() as conn:
            return conn.execute(stmt).first()

    def count(eng, table, *where):
        return one(eng, select(func.count()).select_from(table).where(*where))[0]

    results = []
    for e in entries:
        kind, key = e["type"], e["key"]
        oid = key.get("order_id")
        if oid in deleted_orders and kind not in ("deleted_order",):
            continue  # the order was deleted later, nothing left to check
        if kind in ("new_review", "duplicate_review", "bad_review_score") and key["review_id"] in deleted_review_ids:
            continue  # that review was deleted later
        ok = None
        if kind == "new_order":
            ok = count(ora, o, o.c.order_id == oid) == 1
        elif kind == "status_update":
            ok = one(ora, select(o.c.order_status).where(o.c.order_id == oid))[0] == final_status[oid]
        elif kind in ("mixed_case", "address_change"):
            row = one(my, select(c.c.customer_city, c.c.customer_state).where(c.c.customer_id == key["customer_id"]))
            ok = row is not None and tuple(row) == final_customer[key["customer_id"]]
        elif kind == "negative_price":
            ok = count(ora, i, i.c.order_id == oid, i.c.price < 0) >= 1
        elif kind == "orphan_order":
            ok = (count(ora, o, o.c.order_id == oid) == 1
                  and count(my, c, c.c.customer_id == e["detail"]["customer_id"]) == 0)
        elif kind == "order_without_items":
            ok = count(ora, o, o.c.order_id == oid) == 1 and count(ora, i, i.c.order_id == oid) == 0
        elif kind == "null_estimated_date":
            ok = one(ora, select(o.c.order_estimated_delivery_date).where(o.c.order_id == oid))[0] is None
        elif kind == "impossible_timeline":
            row = one(ora, select(o.c.order_delivered_customer_date, o.c.order_purchase_timestamp).where(o.c.order_id == oid))
            ok = row[0] < row[1]
        elif kind == "duplicate_review":
            ok = count(my, r, r.c.review_id == key["review_id"]) >= 2
        elif kind == "bad_review_score":
            row = one(my, select(r.c.review_score).where(r.c.review_id == key["review_id"]))
            ok = row is not None and not 1 <= row[0] <= 5
        elif kind == "new_review":
            ok = count(my, r, r.c.review_id == key["review_id"]) >= 1
        elif kind == "deleted_review":
            ok = count(my, r, r.c.review_pk == key["review_pk"], r.c.review_id == e["detail"]["review_id"]) == 0
        elif kind == "deleted_order":
            ok = (count(ora, o, o.c.order_id == oid) == 0 and count(ora, i, i.c.order_id == oid) == 0
                  and count(ora, p, p.c.order_id == oid) == 0)
        if ok is not None:
            results.append((e["system"], e["table"], kind, json.dumps(key)[:40], "found" if ok else "MISMATCH", ok))
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--data-dir", default=str(REPO / "sources" / "olist_data"))
    ap.add_argument("--changes", help="path to the simulator's change log (jsonl)")
    ap.add_argument("--md", action="store_true", help="print a markdown table")
    ap.add_argument("--out", help="write the markdown table to this file (UTF-8). Use this instead of > on Windows")
    args = ap.parse_args(argv)

    engines = {s: get_engine(s) for s in ("oracle", "mysql", "postgres")}
    results = changes(args, engines) if args.changes else baseline(args, engines)
    header = ("system", "table", "check", "csv/log", "database", "result")
    rows = [(a, b, c, str(d), str(e), "PASS" if f else "FAIL") for a, b, c, d, e, f in results]
    lines = []
    if args.md or args.out:
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + " --- |" * len(header))
        lines.extend("| " + " | ".join(r) + " |" for r in rows)
    else:
        widths = [max(len(x) for x in col) for col in zip(header, *rows)]
        lines.extend("  ".join(x.ljust(w) for x, w in zip(r, widths)) for r in (header, *rows))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print(f"Wrote {args.out}")
    else:
        print("\n".join(lines))
    failed = sum(1 for r in rows if r[-1] == "FAIL")
    print(f"\n{len(rows) - failed} passed, {failed} failed.", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
