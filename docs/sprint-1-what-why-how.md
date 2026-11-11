# Sprint 1: what we did, why, and how we tested it

Sprint 1 goal: **three source databases, loaded with the Olist dataset, proven correct, with a way to simulate daily changes, so that Sprint 2 can copy them into Snowflake.**

## 1. Story by story

| Story | What we did | Why | How we tested it |
| --- | --- | --- | --- |
| S1-01 Repo and project board | GitHub repo, board, issue per story, branch and PR rules | work is traceable and reviewable | CI runs on every PR |
| S1-02 Dataset profile | `scripts/inspect_csvs.py` reads all 9 CSVs: rows, nulls, duplicates, key problems | know the data before designing tables | output saved in `docs/evidence/` and compared with Kaggle's published description |
| S1-03 Design of the three databases | Tables split by system: Oracle (orders, items, payments), MySQL (customers, reviews), PostgreSQL (products, sellers, categories, geolocation); DDL in `sources/*/01_ddl.sql` | a real company keeps data in several systems, so the pipeline must join across them | DDL applied to real PostgreSQL 16 in my test; 6 SQLite end-to-end tests |
| S1-04 Requirements | `docs/01-requirements.md` v2, KPIs reviewed after mentor feedback | agree what the dashboard must answer | external: mentor approval |
| S1-05 Source loader | `sources/load_olist.py` loads CSVs in chunks, one transaction per table | repeatable; interruption leaves a table empty, never half full | pytest loads sample CSVs and checks counts |
| S1-06 Databases on EC2 | `infra/aws/docker-compose.yml`, `bootstrap_ec2.sh`, `scripts/aws_host.py` | shared copy reachable from any laptop; scripted so it can be rebuilt | `tests/test_aws_host.py` (6 moto tests); on the real server: `docker compose ps` and verification |
| S1-07 PostgreSQL | PostgreSQL 16 with `wal_level=logical` on the same EC2 server (ADR 0005) | Fivetran needs logical replication; RDS adds cost and is not required | `SHOW wal_level` returns `logical` on the server |
| S1-08 DBeaver | three local and three AWS connections | look at the data by hand | screenshots |
| S1-09 Load verification | `sources/verify_load.py`: 30 checks | "the script ran" is not proof | section 3 below |
| S1-10 Change simulator | `sources/daily_changes.py` adds orders, updates statuses, moves customers, injects dirty rows, writes a log | Sprint 3 needs changes to prove incremental loads, SCD2 and data quality tests | `verify_load.py --changes` checks every log entry |
| S1-11 Ingestion readiness | profile of the loaded data, list of known dirty rows, Fivetran notes | Sprint 2 starts with a clear list of risks | document review |

## 2. Key decisions and reasons

- **Local first, then AWS.** Sign-in to AWS was blocked for a day. The same containers run everywhere, so nothing was lost.
- **Keep source column names**, including the dataset's typo `product_name_lenght`. Cleaning happens in Silver (dbt), not at the source, because the source system is supposed to be raw.
- **No CHECK constraints** and no cross-database foreign keys. Real sources are messy, and the simulator injects dirt on purpose so Silver has something to clean.
- **Zip prefixes stored as text (VARCHAR(5))**, otherwise `01046` becomes `1046`.
- **Surrogate keys** `review_pk` and `geolocation_id`, because `review_id` repeats in the data.
- **One EC2, no RDS** (ADR 0005).
- **Env-file switch** (`KLARITY_ENV_FILE`) and a printout of the target servers, so a destructive `--reload` cannot hit the cloud copy by accident; on a remote host it asks you to type `yes`.
- **Per-laptop firewall labels** (`allow-my-ip --label office`) so two laptops never overwrite each other's access, and no port is ever open to the world.

## 3. The 30 checks in `verify_load.py`

Each check computes a value from the CSV and the same value from the database. They must be equal.

**Table checks (25)**

| # | Table (database) | Check | What it catches |
| --- | --- | --- | --- |
| 1 | orders (Oracle) | row count | lost or doubled rows |
| 2 | orders | distinct order_id | duplicate keys |
| 3 | orders | min purchase date | wrong date conversion |
| 4 | orders | max purchase date | same, at the other end |
| 5 | orders | nulls order_approved_at | blanks turned into text or dropped |
| 6 | orders | nulls order_delivered_customer_date | same for another column |
| 7 | order_items (Oracle) | row count | |
| 8 | order_items | sum price | rounding or decimal problems |
| 9 | order_items | sum freight_value | same |
| 10 | order_items | distinct product_id | wrong product references |
| 11 | order_payments (Oracle) | row count | |
| 12 | order_payments | sum payment_value | money mismatch |
| 13 | customers (MySQL) | row count | |
| 14 | customers | distinct customer_unique_id | repeat customers kept correctly |
| 15 | order_reviews (MySQL) | row count | |
| 16 | order_reviews | distinct review_id | duplicated review ids preserved |
| 17 | order_reviews | sum review_score | wrong score values |
| 18 | products (PostgreSQL) | row count | |
| 19 | products | nulls product_category_name | missing categories preserved |
| 20 | products | sum product_weight_g | numeric conversion |
| 21 | sellers (PostgreSQL) | row count | |
| 22 | sellers | distinct seller_state | text kept intact |
| 23 | category_translation | row count | |
| 24 | geolocation | row count | the biggest table (about 1 million rows) |
| 25 | geolocation | distinct zip prefix | leading zeros kept |

**Cross-database link checks (5)**: the number of rows pointing at something that does not exist must be the same in the CSVs and the databases.

| # | Link | Meaning |
| --- | --- | --- |
| 26 | orders.customer_id to customers (Oracle to MySQL) | orders without a customer |
| 27 | order_items.product_id to products (Oracle to PostgreSQL) | items without a product |
| 28 | order_items.seller_id to sellers (Oracle to PostgreSQL) | items without a seller |
| 29 | order_reviews.order_id to orders (MySQL to Oracle) | reviews without an order |
| 30 | products.product_category_name to category_translation | products with an unknown category |

This matters because the databases cannot enforce these links themselves; the pipeline must handle orphans in Silver.

**Change mode (`--changes`)** reads the simulator log and checks each entry in the databases: new orders exist, status updates are the final value, customer moves are applied, injected dirt (negative price, orphan order, order without items, missing estimated date, impossible timeline, duplicate review, bad score) is really present, and deleted rows are gone. If the same row was changed twice, the last change wins; if it was deleted later, the entry is skipped.

## 4. The 12 pytest tests

- `tests/test_pipeline_sqlite.py` (6): loader, verifier and simulator run end to end on SQLite, including a run that checks `--changes`.
- `tests/test_aws_host.py` (6): `aws_host.py` against a fake AWS (moto): status, stop and start update the settings file, `allow-my-ip` opens all four ports, replaces an old IP, keeps two laptops separate, is idempotent, and refuses to create a missing settings file.

## 5. Honest limits

- The loader and verifier share the same value-conversion rules, so a mistake in those rules would affect both sides. Mitigation: look at the data in DBeaver and compare a few rows by eye.
- Tests ran on SQLite and on real PostgreSQL 16. Oracle and MySQL code paths are proven only by running the scripts on real servers (Block 5 of the plan).
- `bootstrap_ec2.sh` and the Docker compose file were syntax-checked but not run on a real EC2 until you run them.
- Simulator runs on AWS will not be identical to local runs; use the new log.
- Fivetran's Oracle connector may not support XE and may need a paid plan. Check in Sprint 2 before relying on it; the fallback needs an ADR.
