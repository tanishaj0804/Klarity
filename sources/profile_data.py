"""Profile the three source databases and write the evidence file for story S1-11.

It runs the profiling queries for you, counts how many rows are affected, and writes a
markdown table with the business impact and the cleaning rule Silver will use.

Usage (repo root, venv active, databases loaded):
    python sources/profile_data.py
    python sources/profile_data.py --out docs/evidence/s1-11-data-profile.md --sql-dir sql/profiling

Read-only: it never changes data.
"""
import argparse
import sys
from pathlib import Path

from sqlalchemy import select

from klarity_db import REPO, SYSTEM_OF, T, get_engine

# Each issue: id, title, system, count query (rows affected), total query (rows checked),
# business impact, cleaning rule. SQL is written to run unchanged on Oracle, MySQL and PostgreSQL.
CORE = [
    ("1", "Duplicate review_id", "mysql",
     "SELECT COALESCE(SUM(c - 1), 0) FROM (SELECT review_id, COUNT(*) c FROM order_reviews "
     "GROUP BY review_id HAVING COUNT(*) > 1) d",
     "SELECT COUNT(*) FROM order_reviews",
     "Reviews are counted twice, so review counts are inflated and average scores can be skewed.",
     "Keep one row per review_id (the latest answer), send the rest to quarantine with a reason code."),
    ("2", "Orders without any items", "oracle",
     "SELECT COUNT(*) FROM orders o LEFT JOIN order_items i ON i.order_id = o.order_id WHERE i.order_id IS NULL",
     "SELECT COUNT(*) FROM orders",
     "An inner join silently drops these orders, so order counts and cancellation rates come out wrong.",
     "Use a left join. Exclude from revenue, keep for cancellation rate."),
    ("3", "Delivered orders with no delivery date", "oracle",
     "SELECT COUNT(*) FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL",
     "SELECT COUNT(*) FROM orders WHERE order_status = 'delivered'",
     "The on-time delivery rate cannot be computed for these orders.",
     "Exclude from the on-time rate and quarantine with reason 'delivered without date'."),
    ("4", "Products without a category", "postgres",
     "SELECT COUNT(*) FROM products WHERE product_category_name IS NULL",
     "SELECT COUNT(*) FROM products",
     "Revenue by category would show a blank group, or drop these products from category reports.",
     "Label the category 'unknown' so the revenue still adds up."),
    ("5", "Categories missing from the translation table", "postgres",
     "SELECT COUNT(DISTINCT p.product_category_name) FROM products p LEFT JOIN category_translation t "
     "ON t.product_category_name = p.product_category_name "
     "WHERE p.product_category_name IS NOT NULL AND t.product_category_name IS NULL",
     "SELECT COUNT(DISTINCT product_category_name) FROM products",
     "These categories show in Portuguese, or disappear, in English reports.",
     "Fall back to the Portuguese name when there is no translation."),
    ("6", "One person with several customer_id values", "mysql",
     "SELECT COUNT(*) - COUNT(DISTINCT customer_unique_id) FROM customers",
     "SELECT COUNT(*) FROM customers",
     "Every order gets a new customer_id, so counting customers by customer_id makes repeat buyers look like new customers.",
     "All customer KPIs (new customers, repeat rate, cohorts, lifetime value) use customer_unique_id."),
    ("7", "Many geolocation rows per zip prefix", "postgres",
     "SELECT COUNT(*) - COUNT(DISTINCT geolocation_zip_code_prefix) FROM geolocation",
     "SELECT COUNT(*) FROM geolocation",
     "Joining customers or sellers to geolocation multiplies their rows and inflates revenue.",
     "Collapse to one row per zip prefix (average coordinates) before any join."),
]

# These exist only after the simulator has run (or if the real data contains them).
INJECTED = [
    ("A", "Negative or zero item price", "oracle",
     "SELECT COUNT(*) FROM order_items WHERE price <= 0", "SELECT COUNT(*) FROM order_items",
     "Revenue is understated and average order value is wrong.",
     "Quarantine the row with reason 'invalid price'."),
    ("B", "Delivered before purchased", "oracle",
     "SELECT COUNT(*) FROM orders WHERE order_delivered_customer_date < order_purchase_timestamp",
     "SELECT COUNT(*) FROM orders",
     "Impossible lead times pull the delivery KPIs down.",
     "Quarantine with reason 'impossible timeline'."),
    ("C", "Order with no estimated delivery date", "oracle",
     "SELECT COUNT(*) FROM orders WHERE order_estimated_delivery_date IS NULL",
     "SELECT COUNT(*) FROM orders",
     "On-time delivery cannot be judged without the promised date.",
     "Exclude from the on-time rate."),
    ("D", "Mixed-case city or state", "mysql",
     "SELECT COUNT(*) FROM customers WHERE customer_city{BIN} <> LOWER(customer_city) "
     "OR customer_state{BIN} <> UPPER(customer_state)",
     "SELECT COUNT(*) FROM customers",
     "The same city or state is counted as two groups in geographic reports.",
     "Standardise: city lower case, state upper case."),
    ("E", "Review score outside 1 to 5", "mysql",
     "SELECT COUNT(*) FROM order_reviews WHERE review_score NOT BETWEEN 1 AND 5",
     "SELECT COUNT(*) FROM order_reviews",
     "Average review score is distorted.",
     "Quarantine with reason 'score out of range'. Add an accepted_values test."),
]


def fmt(dialect, sql):
    """MySQL compares text case-insensitively by default. Force a case-sensitive comparison there."""
    return sql.replace("{BIN}", " COLLATE utf8mb4_bin" if dialect == "mysql" else "")


def scalar(engine, sql):
    with engine.connect() as conn:
        value = conn.exec_driver_sql(sql).scalar()
    return int(value or 0)


def orphans(engines):
    """Cross-database links that no database can enforce."""
    def ids(table, column):
        with engines[SYSTEM_OF[table]].connect() as conn:
            return [r[0] for r in conn.execute(select(T[table].c[column]))]
    checks = [("8", "Orders whose customer is missing from MySQL", "orders", "customer_id", "customers", "customer_id",
               "These orders cannot be tied to a customer, so they drop out of customer reports.",
               "Keep the order, flag it as 'customer unknown', and report the count."),
              ("9", "Reviews whose order is missing from Oracle", "order_reviews", "order_id", "orders", "order_id",
               "Reviews with no order cannot be linked to a seller or category.",
               "Quarantine with reason 'orphan review'.")]
    rows = []
    for num, title, child, ccol, parent, pcol, impact, rule in checks:
        parent_ids = set(ids(parent, pcol))
        child_ids = ids(child, ccol)
        bad = sum(1 for v in child_ids if v is not None and v not in parent_ids)
        rows.append((num, title, f"{SYSTEM_OF[child]} to {SYSTEM_OF[parent]}", bad, len(child_ids), impact, rule,
                     f"-- checked in Python: {child}.{ccol} not found in {parent}.{pcol}"))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", default=str(REPO / "docs" / "evidence" / "s1-11-data-profile.md"))
    ap.add_argument("--sql-dir", default=str(REPO / "sql" / "profiling"),
                    help="folder where the profiling queries are saved, one file per database")
    args = ap.parse_args(argv)

    engines = {s: get_engine(s) for s in ("oracle", "mysql", "postgres")}
    results, by_system = [], {"oracle": [], "mysql": [], "postgres": []}
    for group in (CORE, INJECTED):
        for num, title, system, count_sql, total_sql, impact, rule in group:
            dialect = engines[system].dialect.name  # sqlite in the automated tests
            affected = scalar(engines[system], fmt(dialect, count_sql))
            total = scalar(engines[system], fmt(dialect, total_sql))
            results.append((num, title, system, affected, total, impact, rule))
            by_system[system].append(f"-- {num}. {title}\n{fmt(system, count_sql)};\n")
    for num, title, route, bad, total, impact, rule, note in orphans(engines):
        results.append((num, title, route, bad, total, impact, rule))

    def pct(a, t):
        return "0%" if not a else f"{100 * a / t:.2f}%" if t else "n/a"

    lines = ["# S1-11 evidence: data profile", "",
             "Generated by `python sources/profile_data.py`. Each row is a data problem found in the source",
             "systems, how many rows it touches, why it matters, and the rule Silver will apply.", "",
             "Issues 1 to 9 come from the data itself. Issues A to E are the problems the simulator injects, so they",
             "show as 0 if the simulator has not run yet.", "",
             "| # | Issue | Where | Rows affected | Rows checked | Share | Business impact | Silver rule |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for num, title, where, affected, total, impact, rule in results:
        lines.append(f"| {num} | {title} | {where} | {affected:,} | {total:,} | {pct(affected, total)} | {impact} | {rule} |")
    lines += ["", "## Notes for the demo", "",
              "- Issues 1 to 7 exist in the original Olist data, so they are real findings and not only injected ones.",
              "- Add one sentence here about the result that surprised you most.",
              "- The queries are saved in `sql/profiling/` so anyone can re-run them in DBeaver."]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    sql_dir = Path(args.sql_dir)
    sql_dir.mkdir(parents=True, exist_ok=True)
    for system, parts in by_system.items():
        (sql_dir / f"profile_{system}.sql").write_text(
            f"-- Profiling queries for {system}. Each returns the number of rows affected.\n\n" + "\n".join(parts),
            encoding="utf-8", newline="\n")
    print(f"Wrote {out} and {sql_dir}/profile_*.sql")
    for num, title, where, affected, total, *_ in results:
        print(f"  {num:<2} {title:<50} {affected:>10,} of {total:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
