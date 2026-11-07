"""Check the Olist CSVs against the expected columns and print basic profile figures.

Usage (from the repo root, venv active):
    python scripts/inspect_csvs.py                    # reads sources/olist_data
    python scripts/inspect_csvs.py --dir other_folder
    python scripts/inspect_csvs.py --out docs/evidence/s1-03-csv-profile.md
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

# file name -> (expected columns, key columns for the duplicate check, approx. rows)
EXPECTED = {
    "olist_orders_dataset.csv": (
        ["order_id", "customer_id", "order_status", "order_purchase_timestamp",
         "order_approved_at", "order_delivered_carrier_date",
         "order_delivered_customer_date", "order_estimated_delivery_date"],
        ["order_id"], 99441),
    "olist_order_items_dataset.csv": (
        ["order_id", "order_item_id", "product_id", "seller_id",
         "shipping_limit_date", "price", "freight_value"],
        ["order_id", "order_item_id"], 112650),
    "olist_order_payments_dataset.csv": (
        ["order_id", "payment_sequential", "payment_type",
         "payment_installments", "payment_value"],
        ["order_id", "payment_sequential"], 103886),
    "olist_customers_dataset.csv": (
        ["customer_id", "customer_unique_id", "customer_zip_code_prefix",
         "customer_city", "customer_state"],
        ["customer_id"], 99441),
    "olist_order_reviews_dataset.csv": (
        ["review_id", "order_id", "review_score", "review_comment_title",
         "review_comment_message", "review_creation_date", "review_answer_timestamp"],
        ["review_id"], 99224),
    "olist_products_dataset.csv": (
        ["product_id", "product_category_name", "product_name_lenght",
         "product_description_lenght", "product_photos_qty", "product_weight_g",
         "product_length_cm", "product_height_cm", "product_width_cm"],
        ["product_id"], 32951),
    "olist_sellers_dataset.csv": (
        ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
        ["seller_id"], 3095),
    "product_category_name_translation.csv": (
        ["product_category_name", "product_category_name_english"],
        ["product_category_name"], 71),
    "olist_geolocation_dataset.csv": (
        ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
         "geolocation_city", "geolocation_state"],
        ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng"], 1000163),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="sources/olist_data")
    parser.add_argument("--md", action="store_true", help="print a markdown table")
    parser.add_argument("--out", help="write the markdown table to this file (UTF-8)")
    args = parser.parse_args()
    folder = Path(args.dir)

    rows, problems = [], 0
    for name, (columns, keys, approx) in EXPECTED.items():
        path = folder / name
        if not path.exists():
            rows.append((name, "MISSING", "", "", "", ""))
            problems += 1
            continue
        df = pd.read_csv(path, dtype=str, encoding="utf-8")
        cols_ok = list(df.columns) == columns
        dups = int(df.duplicated(subset=keys).sum())
        nulls = int(df.isna().any(axis=1).sum())
        if not cols_ok:
            problems += 1
        rows.append((name, f"{len(df):,}", f"{approx:,}",
                     "yes" if cols_ok else "NO", f"{dups:,}", f"{nulls:,}"))

    header = ("file", "rows", "expected approx.", "columns match",
              "duplicate keys", "rows with any null")
    lines = []
    if args.md or args.out:
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + " --- |" * len(header))
        lines.extend("| " + " | ".join(r) + " |" for r in rows)
    else:
        widths = [max(len(str(x)) for x in col) for col in zip(header, *rows)]
        lines.extend("  ".join(str(x).ljust(w) for x, w in zip(r, widths)) for r in (header, *rows))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print(f"Wrote {args.out}")
    else:
        print("\n".join(lines))
    print(f"\n{problems} problem(s) found.", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
