"""Tests for the reconciliation logic and the fallback loader's reader (no Snowflake needed)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sources"))
sys.path.insert(0, str(ROOT / "scripts"))

import reconcile_bronze as rb  # noqa: E402


SCHEMAS = {"oracle": "ORACLE_KLARITY_APP", "mysql": "MYSQL_CRM", "postgres": "PG_PUBLIC"}


def test_bronze_sql_ignores_deleted_rows():
    sql = rb.bronze_sql("PG_PUBLIC", "products", "rows", None)
    assert sql == "SELECT COUNT(*) FROM BRONZE.PG_PUBLIC.PRODUCTS WHERE COALESCE(_FIVETRAN_DELETED, FALSE) = FALSE"
    assert "SUM(PRICE)" in rb.bronze_sql("X", "order_items", "sum", "price")


def test_reconcile_pass_and_fail_and_skip():
    source = lambda t, k, c: 10  # noqa: E731
    good = rb.reconcile(source, lambda sql: 10, SCHEMAS, skip={"geolocation"})
    assert good and all(r[5] for r in good) and not any(r[1] == "geolocation" for r in good)
    bad = rb.reconcile(source, lambda sql: 9 if "ORDER_PAYMENTS" in sql else 10, SCHEMAS)
    assert {r[1] for r in bad if not r[5]} == {"order_payments"}


def test_reconcile_tolerates_float_rounding_on_money():
    out = rb.reconcile(lambda t, k, c: 100.004, lambda sql: 100.0, SCHEMAS)
    assert all(r[5] for r in out)


def test_fallback_reader_adds_fivetran_columns(tmp_path, monkeypatch):
    monkeypatch.setenv("KLARITY_SQLITE_DIR", str(tmp_path))
    import importlib
    import klarity_db
    importlib.reload(klarity_db)
    import load_oracle_to_snowflake as fb
    importlib.reload(fb)
    from sqlalchemy import insert
    engine = klarity_db.get_engine("oracle")
    klarity_db.META.create_all(engine, tables=[klarity_db.T["orders"]])
    with engine.begin() as conn:
        conn.execute(insert(klarity_db.T["orders"]), [{"order_id": "o1", "customer_id": "c1", "order_status": "delivered"}])
    frames = list(fb.read_table(engine, "orders"))
    assert len(frames) == 1 and list(frames[0]["ORDER_ID"]) == ["o1"]
    assert frames[0]["_FIVETRAN_DELETED"].tolist() == [False]
    assert "_FIVETRAN_SYNCED" in frames[0].columns


def test_quarantine_comparison_logic(tmp_path):
    import json
    import check_quarantine_vs_log as q
    log = tmp_path / "log.jsonl"
    entries = [
        {"type": "negative_price", "key": {"order_id": "a"}},
        {"type": "negative_price", "key": {"order_id": "b"}},
        {"type": "orphan_order", "key": {"order_id": "c"}},
        {"type": "deleted_order", "key": {"order_id": "c"}},   # deleted later: cannot be quarantined
    ]
    log.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")
    injected = q.injected_counts(log)
    assert injected["negative_price"] == 2 and injected.get("orphan_order", 0) == 0
    ok = q.compare(injected, {("order_items", "invalid_price"): 5})
    assert all(r[4] for r in ok)
    bad = q.compare(injected, {("order_items", "invalid_price"): 1})
    assert [r[0] for r in bad if not r[4]] == ["negative_price"]
