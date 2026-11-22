"""Remove the customers left behind by an interrupted simulator run.

The simulator writes new customers to MySQL first and the new orders to Oracle second. If the Oracle
step fails, MySQL keeps customers that have no order and that are in no change log.

How the script finds them (all three must be true):
  1. the customer exists in MySQL,
  2. no Oracle order points at it,
  3. Bronze has never seen it before today (not in Bronze, or Bronze row synced today or later).
Rule 3 protects the few customers without orders that were there from the start of the project.

    python scripts/cleanup_interrupted_run.py --expect 48              # dry run: shows what it would delete
    python scripts/cleanup_interrupted_run.py --expect 48 --execute    # deletes them

It refuses to delete anything unless the number found equals --expect.
Settings come from the .env file chosen with KLARITY_ENV_FILE (use .env.aws for the AWS databases).
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sources"))

from klarity_db import T, describe_targets, get_engine  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402


def bronze_customers(cutoff):
    """{customer_id: synced_at} for Bronze customers, plus the ids that are older than the cutoff."""
    from klarity_snowflake import BRONZE_SCHEMA, connect

    conn = connect(database="BRONZE")
    cur = conn.cursor()
    cur.execute(f'select "customer_id", "_fivetran_synced" from BRONZE."{BRONZE_SCHEMA["mysql"]}"."customers"')
    seen, old = set(), set()
    for cid, synced in cur.fetchall():
        seen.add(cid)
        if synced is not None:
            if synced.tzinfo is None:
                synced = synced.replace(tzinfo=timezone.utc)
            if synced < cutoff:
                old.add(cid)
    conn.close()
    return seen, old


def find_candidates(mysql_ids, oracle_customer_ids, bronze_old_ids):
    without_order = set(mysql_ids) - set(oracle_customer_ids)
    return sorted(without_order - set(bronze_old_ids)), without_order


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--expect", type=int, required=True, help="how many customers you expect to remove")
    ap.add_argument("--execute", action="store_true", help="really delete (default is a dry run)")
    ap.add_argument("--since", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    help="Bronze rows synced before this UTC date count as old (default: today)")
    a = ap.parse_args()
    cutoff = datetime.fromisoformat(a.since).replace(tzinfo=timezone.utc)

    print(describe_targets(["mysql", "oracle"]))
    my, ora = get_engine("mysql"), get_engine("oracle")
    with my.connect() as c:
        mysql_ids = [r[0] for r in c.execute(select(T["customers"].c.customer_id))]
    with ora.connect() as c:
        oracle_ids = {r[0] for r in c.execute(select(T["orders"].c.customer_id))}
    _, old_ids = bronze_customers(cutoff)
    found, without_order = find_candidates(mysql_ids, oracle_ids, old_ids)

    print(f"MySQL customers: {len(mysql_ids)}")
    print(f"  without any Oracle order: {len(without_order)}")
    print(f"  of those, known to Bronze before {a.since} (kept): {len(without_order) - len(found)}")
    print(f"  to remove: {len(found)}   (expected {a.expect})")
    if len(found) != a.expect:
        print("STOP: the number found is not the number expected. Nothing was deleted.", file=sys.stderr)
        return 2
    for cid in found[:5]:
        print("  e.g.", cid)
    if not a.execute:
        print("Dry run only. Add --execute to delete.")
        return 0
    with my.begin() as c:
        for i in range(0, len(found), 500):
            c.execute(delete(T["customers"]).where(T["customers"].c.customer_id.in_(found[i:i + 500])))
    print(f"Deleted {len(found)} customers from MySQL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
