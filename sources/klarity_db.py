"""Shared database layer for the Klarity source systems (Oracle, MySQL, PostgreSQL).

One place that knows: which table lives in which database, the column types, how to
connect, and how to turn CSV text into typed Python values.

Set KLARITY_SQLITE_DIR to run everything against local SQLite files. That is used by
the automated tests only, never for the real project.
"""
import os
import re
import warnings
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (BigInteger, Column, DateTime, Float, Integer, MetaData,
                        Numeric, SmallInteger, String, Table, Text, create_engine)
from sqlalchemy.engine import URL

warnings.filterwarnings("ignore", message=".*Decimal.*")

# Which settings file to use. Default: .env. To aim the scripts at AWS instead of your laptop:
#   PowerShell:  $env:KLARITY_ENV_FILE = ".env.aws"
ENV_FILE = os.environ.get("KLARITY_ENV_FILE")
load_dotenv(ENV_FILE) if ENV_FILE else load_dotenv()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

SYSTEMS = ["oracle", "mysql", "postgres"]

# Tables in load order (parents first). Delete in the reverse order.
LOAD_ORDER = {
    "oracle": ["orders", "order_items", "order_payments"],
    "mysql": ["customers", "order_reviews"],
    "postgres": ["category_translation", "products", "sellers", "geolocation"],
}
SYSTEM_OF = {t: s for s, tables in LOAD_ORDER.items() for t in tables}

CSV_OF = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    "geolocation": "olist_geolocation_dataset.csv",
}

DDL_FILE = {
    "oracle": HERE / "oracle" / "01_ddl.sql",
    "mysql": HERE / "mysql" / "01_ddl.sql",
    "postgres": HERE / "postgres" / "01_ddl.sql",
}

META = MetaData()
S = String
KEY = BigInteger().with_variant(Integer, "sqlite")  # surrogate keys


def _t(name, *cols):
    return Table(name, META, *cols)


_t("orders",
   Column("order_id", S(32), primary_key=True), Column("customer_id", S(32)),
   Column("order_status", S(20)), Column("order_purchase_timestamp", DateTime),
   Column("order_approved_at", DateTime), Column("order_delivered_carrier_date", DateTime),
   Column("order_delivered_customer_date", DateTime),
   Column("order_estimated_delivery_date", DateTime))
_t("order_items",
   Column("order_id", S(32), primary_key=True), Column("order_item_id", Integer, primary_key=True),
   Column("product_id", S(32)), Column("seller_id", S(32)), Column("shipping_limit_date", DateTime),
   Column("price", Numeric(10, 2)), Column("freight_value", Numeric(10, 2)))
_t("order_payments",
   Column("order_id", S(32), primary_key=True), Column("payment_sequential", Integer, primary_key=True),
   Column("payment_type", S(20)), Column("payment_installments", Integer),
   Column("payment_value", Numeric(10, 2)))
_t("customers",
   Column("customer_id", S(32), primary_key=True), Column("customer_unique_id", S(32)),
   Column("customer_zip_code_prefix", S(5)), Column("customer_city", S(64)),
   Column("customer_state", S(2)))
_t("order_reviews",
   Column("review_pk", KEY, primary_key=True, autoincrement=True),
   Column("review_id", S(32)), Column("order_id", S(32)), Column("review_score", SmallInteger),
   Column("review_comment_title", S(255)), Column("review_comment_message", Text),
   Column("review_creation_date", DateTime), Column("review_answer_timestamp", DateTime))
_t("products",
   Column("product_id", S(32), primary_key=True), Column("product_category_name", S(80)),
   Column("product_name_lenght", Integer), Column("product_description_lenght", Integer),
   Column("product_photos_qty", Integer), Column("product_weight_g", Integer),
   Column("product_length_cm", Integer), Column("product_height_cm", Integer),
   Column("product_width_cm", Integer))
_t("sellers",
   Column("seller_id", S(32), primary_key=True), Column("seller_zip_code_prefix", S(5)),
   Column("seller_city", S(64)), Column("seller_state", S(2)))
_t("category_translation",
   Column("product_category_name", S(80), primary_key=True),
   Column("product_category_name_english", S(80)))
_t("geolocation",
   Column("geolocation_id", KEY, primary_key=True, autoincrement=True),
   Column("geolocation_zip_code_prefix", S(5)), Column("geolocation_lat", Float),
   Column("geolocation_lng", Float), Column("geolocation_city", S(64)),
   Column("geolocation_state", S(2)))

T = META.tables

# Columns that exist only in the database (surrogate keys), never in the CSV.
SURROGATE = {"review_pk", "geolocation_id"}


def csv_columns(table_name):
    return [c.name for c in T[table_name].columns if c.name not in SURROGATE]


def tables_for(system):
    return [T[n] for n in LOAD_ORDER[system]]


def _env(name, default=None):
    value = os.environ.get(name, default)
    if value in (None, ""):
        raise RuntimeError(f"Missing {name}. Fill it in your .env file (see .env.example).")
    return value


def get_engine(system):
    sqlite_dir = os.environ.get("KLARITY_SQLITE_DIR")
    if sqlite_dir:
        return create_engine(f"sqlite:///{Path(sqlite_dir) / (system + '.db')}")
    if system == "oracle":
        url = URL.create("oracle+oracledb", username=_env("ORACLE_USER"),
                         password=_env("ORACLE_APP_PASSWORD"), host=_env("ORACLE_HOST"),
                         port=int(_env("ORACLE_PORT", "1521")),
                         query={"service_name": _env("ORACLE_SERVICE", "XEPDB1")})
    elif system == "mysql":
        url = URL.create("mysql+mysqlconnector", username=_env("MYSQL_USER"),
                         password=_env("MYSQL_PASSWORD"), host=_env("MYSQL_HOST"),
                         port=int(_env("MYSQL_PORT", "3306")), database=_env("MYSQL_DATABASE"),
                         query={"charset": "utf8mb4"})
    elif system == "postgres":
        url = URL.create("postgresql+psycopg2", username=_env("PG_USER"),
                         password=_env("PG_PASSWORD"), host=_env("PG_HOST"),
                         port=int(_env("PG_PORT", "5432")), database=_env("PG_DATABASE"))
    else:
        raise ValueError(system)
    return create_engine(url, pool_pre_ping=True)


HOST_VAR = {"oracle": "ORACLE_HOST", "mysql": "MYSQL_HOST", "postgres": "PG_HOST"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def target(system):
    """Where the scripts will connect, for example 'localhost' or '13.233.1.2'."""
    if os.environ.get("KLARITY_SQLITE_DIR"):
        return "sqlite"
    return os.environ.get(HOST_VAR[system], "(not set)")


def is_remote(system):
    return target(system) not in LOCAL_HOSTS | {"sqlite"}


def describe_targets(systems=SYSTEMS):
    """One line per database, so you always see what you are about to change."""
    env = ENV_FILE or ".env"
    lines = [f"  {s:<9}{target(s)}" for s in systems]
    return f"Settings file: {env}\n" + "\n".join(lines)


def split_sql(text):
    """Split a DDL file into single statements (comments removed)."""
    text = re.sub(r"--[^\n]*", "", text)
    return [s.strip() for s in text.split(";") if s.strip()]


def apply_ddl(engine, system):
    """Create the tables for one system. Drops existing ones first (Oracle needs it explicitly)."""
    if engine.dialect.name == "sqlite":
        tables = tables_for(system)
        META.drop_all(engine, tables=tables)
        META.create_all(engine, tables=tables)
        return
    if system == "oracle":
        for name in reversed(LOAD_ORDER["oracle"]):
            with engine.connect() as conn:
                try:
                    conn.exec_driver_sql(f"DROP TABLE {name} PURGE")
                    conn.commit()
                except Exception:
                    conn.rollback()  # table did not exist
    with engine.begin() as conn:
        for stmt in split_sql(DDL_FILE[system].read_text(encoding="utf-8")):
            conn.exec_driver_sql(stmt)


def convert_values(values, sql_type):
    """Turn CSV text into typed Python values. Empty text becomes None."""
    out = []
    for v in values:
        if v is None or v == "":
            out.append(None)
        elif isinstance(sql_type, DateTime):
            out.append(datetime.fromisoformat(v))
        elif isinstance(sql_type, Integer):
            out.append(int(Decimal(v)))
        elif isinstance(sql_type, Float):
            out.append(float(v))
        elif isinstance(sql_type, Numeric):
            out.append(Decimal(v))
        else:
            out.append(v)
    return out
