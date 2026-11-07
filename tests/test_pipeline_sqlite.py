"""End-to-end test of load -> verify -> simulate -> verify changes, on throw-away SQLite files.

Run: python -m pytest tests -q
"""
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sources"))

import daily_changes  # noqa: E402
import klarity_db  # noqa: E402
import load_olist  # noqa: E402
import verify_load  # noqa: E402


def make_csvs(folder, n_orders=60):
    rng = random.Random(1)
    h = lambda: f"{rng.getrandbits(128):032x}"  # noqa: E731
    base = datetime(2017, 5, 1, 10, 0, 0)
    prods = [{"product_id": h(), "product_category_name": rng.choice(["beleza_saude", "esporte_lazer", ""]),
              "product_name_lenght": "40", "product_description_lenght": "300", "product_photos_qty": "2",
              "product_weight_g": str(rng.randint(100, 3000)), "product_length_cm": "20",
              "product_height_cm": "10", "product_width_cm": "15"} for _ in range(12)]
    sellers = [{"seller_id": h(), "seller_zip_code_prefix": "1046", "seller_city": "sao paulo",
                "seller_state": "SP"} for _ in range(5)]
    customers, orders, items, pays, reviews = [], [], [], [], []
    for i in range(n_orders):
        oid, cid = h(), h()
        customers.append({"customer_id": cid, "customer_unique_id": h() if i % 3 else customers[0]["customer_unique_id"] if customers else h(),
                          "customer_zip_code_prefix": "14409", "customer_city": rng.choice(["franca", "campinas", "recife"]),
                          "customer_state": rng.choice(["SP", "PE"])})
        p = base + timedelta(days=i)
        delivered = i % 5 != 0
        orders.append({"order_id": oid, "customer_id": cid, "order_status": "delivered" if delivered else "shipped",
                       "order_purchase_timestamp": p.isoformat(sep=" "), "order_approved_at": (p + timedelta(hours=1)).isoformat(sep=" "),
                       "order_delivered_carrier_date": (p + timedelta(days=2)).isoformat(sep=" "),
                       "order_delivered_customer_date": (p + timedelta(days=9)).isoformat(sep=" ") if delivered else "",
                       "order_estimated_delivery_date": (p + timedelta(days=12)).strftime("%Y-%m-%d 00:00:00")})
        total = 0
        for n in range(1, rng.randint(1, 2) + 1):
            price, freight = round(rng.uniform(10, 200), 2), round(rng.uniform(5, 30), 2)
            total += price + freight
            items.append({"order_id": oid, "order_item_id": str(n), "product_id": rng.choice(prods)["product_id"],
                          "seller_id": rng.choice(sellers)["seller_id"],
                          "shipping_limit_date": (p + timedelta(days=3)).isoformat(sep=" "),
                          "price": f"{price:.2f}", "freight_value": f"{freight:.2f}"})
        pays.append({"order_id": oid, "payment_sequential": "1", "payment_type": "credit_card",
                     "payment_installments": "3", "payment_value": f"{total:.2f}"})
        if delivered:
            reviews.append({"review_id": h(), "order_id": oid, "review_score": str(rng.randint(1, 5)),
                            "review_comment_title": "", "review_comment_message": "Ótimo produto,\nchegou bem",
                            "review_creation_date": (p + timedelta(days=10)).isoformat(sep=" "),
                            "review_answer_timestamp": (p + timedelta(days=11)).isoformat(sep=" ")})
    reviews.append(dict(reviews[0]))  # the real data repeats review_id too
    geo = [{"geolocation_zip_code_prefix": "14409", "geolocation_lat": "-20.5", "geolocation_lng": "-47.4",
            "geolocation_city": "franca", "geolocation_state": "SP"}] * 6
    trans = [{"product_category_name": "beleza_saude", "product_category_name_english": "health_beauty"},
             {"product_category_name": "esporte_lazer", "product_category_name_english": "sports_leisure"}]
    data = {"orders": orders, "order_items": items, "order_payments": pays, "customers": customers,
            "order_reviews": reviews, "products": prods, "sellers": sellers,
            "category_translation": trans, "geolocation": geo}
    for table, rows in data.items():
        pd.DataFrame(rows, columns=klarity_db.csv_columns(table)).to_csv(
            folder / klarity_db.CSV_OF[table], index=False, encoding="utf-8")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("KLARITY_SQLITE_DIR", str(tmp_path))
    data = tmp_path / "csv"
    data.mkdir()
    make_csvs(data)
    return {"data": str(data), "log": str(tmp_path / "change_log.jsonl")}


def test_load_then_verify_passes(env):
    assert load_olist.main(["--data-dir", env["data"], "--ddl"]) == 0
    assert verify_load.main(["--data-dir", env["data"]]) == 0


def test_second_load_is_refused_unless_reload(env):
    assert load_olist.main(["--data-dir", env["data"], "--ddl"]) == 0
    assert load_olist.main(["--data-dir", env["data"]]) == 3
    assert load_olist.main(["--data-dir", env["data"], "--reload"]) == 0
    assert verify_load.main(["--data-dir", env["data"]]) == 0


def test_verify_detects_a_missing_row(env):
    load_olist.main(["--data-dir", env["data"], "--ddl"])
    with klarity_db.get_engine("oracle").begin() as c:
        c.exec_driver_sql("DELETE FROM order_payments WHERE rowid IN (SELECT rowid FROM order_payments LIMIT 1)")
    assert verify_load.main(["--data-dir", env["data"]]) == 1


def test_simulator_changes_are_logged_and_verified(env):
    load_olist.main(["--data-dir", env["data"], "--ddl"])
    # one simulated day every two days: orders need about six runs to travel from created to delivered
    for n in range(8):
        day = ["--now", f"2026-11-{1 + 2 * n:02d}T09:00:00", "--orders", "30", "--updates", "200",
               "--seed", str(n), "--log", env["log"]]
        assert daily_changes.main(day) == 0
    kinds = {json.loads(line)["type"] for line in Path(env["log"]).read_text().splitlines()}
    expected = {"new_order", "status_update", "new_review", "address_change", "mixed_case", "negative_price",
                "orphan_order", "order_without_items", "null_estimated_date", "impossible_timeline",
                "duplicate_review", "bad_review_score", "deleted_review", "deleted_order"}
    assert expected <= kinds, expected - kinds
    assert verify_load.main(["--changes", env["log"]]) == 0


def test_clean_day_injects_no_dirt(env):
    load_olist.main(["--data-dir", env["data"], "--ddl"])
    daily_changes.main(["--now", "2026-11-01T09:00:00", "--dirty", "0", "--seed", "3", "--log", env["log"]])
    kinds = {json.loads(line)["type"] for line in Path(env["log"]).read_text().splitlines()}
    assert kinds <= {"new_order", "status_update", "new_review", "address_change"}


def test_same_seed_gives_same_changes(env, tmp_path):
    load_olist.main(["--data-dir", env["data"], "--ddl"])
    log_a, log_b = str(tmp_path / "a.jsonl"), str(tmp_path / "b.jsonl")
    for log in (log_a, log_b):
        load_olist.main(["--data-dir", env["data"], "--reload"])
        daily_changes.main(["--now", "2026-11-01T09:00:00", "--seed", "9", "--log", log])
    strip = lambda p: [(e["type"], e["key"]) for e in map(json.loads, Path(p).read_text().splitlines())]  # noqa: E731
    assert strip(log_a) == strip(log_b)
