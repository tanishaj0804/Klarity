# Klarity: Snowflake, Fivetran and Silver, step by step

Start: Mon 16 Nov, evening. Target: Silver built and tested by **Wed 18 Nov noon**, so Gold starts the same afternoon. If you are already behind this timing, the Part 9 gates tell you what to cut.

**Where everything is:** unzip `klarity-silver.zip` into your repo and choose Replace. It adds Snowflake SQL, source-database prep scripts, a dbt project (`dbt/klarity`), reconciliation and check scripts, and a fallback Oracle loader. After unzipping, run `python -m pytest tests -q` (expect **19 passed**).

---

## 0. What I found in the docs, and what changed in the plan

| Finding (Fivetran / Snowflake docs, checked today) | What it means for you |
| --- | --- |
| Fivetran's PostgreSQL and MySQL guides require **TLS** on the database for direct connections. Your Docker databases have no certificate set up. | Use Fivetran's **SSH tunnel** option through your EC2 server. Traffic is encrypted by SSH, and only port 22 is opened to Fivetran. The tunnel page lets you turn off "Require TLS through tunnel". |
| Snowflake is discontinuing password authentication; service users use **key pairs**. | Passwords are not used. `scripts/make_snowflake_keys.py` makes the keys. |
| Fivetran publishes IP lists **per cloud and region**. The Mumbai AWS list is `3.111.138.160/29`, but a free account may default to a different region. | Read the IPs from your own connector setup page, and add them with `aws_host.py allow-cidr`. |
| Fivetran's Oracle guide (checked 7 Nov) names the Enterprise/Business Critical plan and needs ARCHIVELOG settings. | Test it on day one; the fallback loader is ready (Part 5). |
| PostgreSQL logical replication needs a publication and a replication slot. | `postgres_fivetran.sql` creates both. |
| I could not confirm the Free plan's exact row limit rules (500,000 monthly active rows was noted on 7 Nov), or whether the first full sync counts. | Geolocation (1M rows) is **not synced**. Watch Fivetran's usage page after each connector. |

**Things I could not verify from here:** I did not run any of this against your real Snowflake, Fivetran, Oracle, MySQL or EC2. The dbt models were run on a small fake Bronze dataset (using a local engine, not Snowflake) and every cleaning rule gave the expected result. Treat Snowflake-specific behaviour as unproven until Gate 3 below. Where a Fivetran screen label may differ from what I describe, I say so.

---

## 1. Add the files and commit (10 min)

```powershell
cd $HOME\Documents\Klarity
git checkout main; git pull
git checkout -b feature/s2-bronze-silver
# unzip klarity-silver.zip here, choose Replace
pip install -r requirements.txt
python -m pytest tests -q                 # 19 passed
git status                                # no .env, no .p8 key, no CSVs should appear
git add .
git commit -m "feat: Snowflake setup, Fivetran source prep, dbt Silver models, reconciliation"
git push -u origin HEAD
```

Open the PR later (Part 8). Commit again as you finish each part, so the history shows your work.

---

## 2. Snowflake (S2-01, S2-02), about 45 min

**Why:** Bronze, Silver and Gold are separate databases with separate roles, so Fivetran can only write Bronze, dbt can write Silver and Gold, and the dashboard can only read Gold. The resource monitor stops spending before the trial credits run out.

1. **Sign up** at snowflake.com (free trial). Choose **Standard** edition, cloud **AWS**, region **Asia Pacific (Mumbai)**. Write down the **sign-up date** and the trial length shown on the page (I could not confirm it; commonly 30 days, which covers 24 Nov).
2. **Find your account identifier.** In Snowsight click your name (bottom left), then Account, then copy the **account identifier** in the form `ORGNAME-ACCOUNTNAME`.
3. **Create the keys** (on your laptop, not in the repo):

   ```powershell
   python scripts/make_snowflake_keys.py
   ```

   It writes three private keys into `C:\Users\<you>\.snowflake_keys\` and prints three one-line public keys.
4. **Edit `infra/snowflake/s2_setup.sql`:** replace the three `<PUBLIC KEY FOR ...>` placeholders with the printed keys (keep the quotes). Don't commit the edited file with real keys (they are public keys, so it is not a secret, but keep the repo version generic anyway). Easiest: copy the file to your Desktop, edit there, paste into Snowsight.
5. **Run it:** in Snowsight, open a new SQL worksheet, paste the whole script, and run it with **Run all**. It switches roles by itself. Everything is re-runnable.
6. **Prove it (save as evidence):** run the four `SHOW` lines at the bottom of the script and screenshot the output. Save to `docs/evidence/s2-02-snowflake-roles.png`. Check that `SHOW RESOURCE MONITORS` lists `KLARITY_MONITOR`.
7. **Put the settings in your `.env`** (copy from `.env.snowflake.example`):

   ```
   SNOWFLAKE_ACCOUNT=ORGNAME-ACCOUNTNAME
   SNOWFLAKE_USER=DBT_USER
   SNOWFLAKE_PRIVATE_KEY_PATH=C:\Users\<you>\.snowflake_keys\dbt_user.p8
   SNOWFLAKE_ROLE=TRANSFORMER
   SNOWFLAKE_WAREHOUSE=TRANSFORM_WH
   ```
8. **Test the login:**

   ```powershell
   python scripts/check_snowflake.py
   ```

   Expected: `Logged in as: user=DBT_USER role=TRANSFORMER warehouse=TRANSFORM_WH` and `Schemas in BRONZE: (none yet)`.

**Gate 1:** `check_snowflake.py` prints that line. Common errors: *JWT token is invalid* means the public key in the SQL doesn't match the `.p8` file (paste the right one, or run `make_snowflake_keys.py --force` and redo step 4); *account not found* means the account identifier is wrong.

---

## 3. Prepare the three source databases (S2-03, S2-07), about 40 min

**Why:** Fivetran gets its own read-only user, so it can never change your sources. Logical replication lets it see inserts, updates and deletes.

Start the server and put your IP in:

```powershell
python scripts/aws_host.py start --env-file .env.aws
python scripts/aws_host.py allow-my-ip --label home
scp -i $HOME\.ssh\klarity-key.pem -r infra\aws\source_prep ubuntu@<SERVER IP>:~/
ssh -i $HOME\.ssh\klarity-key.pem ubuntu@<SERVER IP>
```

On the server. First put real passwords into the two files (use new strong ones and save them in your password manager):

```bash
cd ~/source_prep
sed -i "s/CHANGE_ME_Strong1/ORACLE_RO_PASSWORD_HERE/" oracle_readonly.sql
sed -i "s/CHANGE_ME/MYSQL_FIVETRAN_PASSWORD_HERE/" mysql_fivetran.sql
```

Then run the three scripts. The database containers already know their admin passwords, so nothing is typed:

```bash
# PostgreSQL (klarity_app is the container's superuser, so it may create publications and slots)
sudo docker exec -i klarity-postgres psql -U klarity_app -d catalog -v pw="'NEW_PG_FIVETRAN_PASSWORD'" < postgres_fivetran.sql
# MySQL
sudo docker exec -i klarity-mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD"' < mysql_fivetran.sql
# Oracle read-only user
sudo docker exec -i klarity-oracle sh -c 'sqlplus -s system/"$ORACLE_PASSWORD"@//localhost:1521/XEPDB1' < oracle_readonly.sql
```

Check the printed output: PostgreSQL shows `wal_level = logical`, a publication with 3 tables and a slot; MySQL shows `log_bin ON`, `binlog_format ROW`, and the grants. If MySQL shows different values, send me the lines.

If the PostgreSQL command says the role `klarity_app` does not exist, use the `PG_USER` value from `~/Klarity/infra/aws/.env` instead.

**Proof (S2-03):** connect to PostgreSQL as `fivetran` and try `INSERT INTO sellers (seller_id) VALUES ('x');`. It must be refused. Screenshot it into `docs/evidence/s2-03-readonly-proof.png`.

Leave the SSH session open; Part 4 needs the Fivetran key.

---

## 4. Fivetran: destination and the first two connectors (S2-04, S2-05, S2-07), about 90 min

**Why an SSH tunnel:** see Part 0. Why PostgreSQL first: it is the simplest source, so you learn Fivetran on the lowest-risk system.

### 4.1 Destination

1. In Fivetran: **Destinations, Add destination, Snowflake**. Choose **Snowflake Native Table**.
2. Host: `ORGNAME-ACCOUNTNAME.snowflakecomputing.com`. User: `FIVETRAN_USER`. Database: `BRONZE`. Authentication: **KEY-PAIR**. Open `C:\Users\<you>\.snowflake_keys\fivetran_user.p8` in Notepad and paste its full text (including the BEGIN and END lines). Role: `LOADER`. Warehouse: `FIVETRAN_WH`.
3. **Save & Test.** (Screen labels may differ slightly from this list.) If the test fails with a network error, Snowflake may block Fivetran by network policy; a new trial account normally has none.

### 4.2 PostgreSQL connector

1. **Connectors, Add connector, PostgreSQL.**
2. **Destination schema prefix:** `pg`. This should create the Snowflake schema `PG_PUBLIC` (prefix plus source schema). You confirm it in step 6.
3. **Connection method: SSH tunnel.** Fivetran now shows you an **SSH public key** and its **IP addresses to allow**. Keep this page open.
4. **On the server** (the SSH session from Part 3), create the tunnel user with the key you copied. Keep the whole key on one line, in quotes:

   ```bash
   bash ~/source_prep/ssh_tunnel_user.sh "ssh-rsa AAAA...the key from Fivetran..."
   ```

   It prints the server's private IP.
5. **On your laptop, open port 22 for Fivetran's IPs only** (use the list from the Fivetran page, separated by spaces):

   ```powershell
   python scripts/aws_host.py allow-cidr --label fivetran --cidr <IP-1> <IP-2>
   python scripts/aws_host.py status        # no 0.0.0.0/0 anywhere
   ```
6. **Fill in the connector form:**
   - SSH host: the server's public IP. SSH user: `fivetran`. SSH port: 22.
   - Database host: `127.0.0.1` (the database as seen from the server; the containers publish their ports on the server). Port 5432. If the test fails, use the private IP printed in step 4. (The docs don't state which to use; this is my best reading.)
   - Database `catalog`, user `fivetran`, the password you set.
   - **Require TLS through tunnel:** turn it **off** (your database has no TLS; the SSH tunnel encrypts the traffic).
   - **Update method:** logical replication (**WAL_PGOUTPUT**). Publication `fivetran_pub`. Replication slot `fivetran_pgoutput_slot`.
   - **Save & Test.** Fix any red step before going on. The test confirms the SSH fingerprint; compare it with `ssh-keygen -l` output on the server if you want to be strict.
7. **Schema tab:** include `products`, `sellers`, `category_translation`. **Do not include geolocation.**
8. **Start the initial sync.** Wait until it shows **Synced**.

### 4.3 MySQL connector

Same pattern: Add connector, MySQL, **schema prefix `mysql`** (should give `MYSQL_CRM`), SSH tunnel with the same `fivetran` OS user (each connector shows its own key: run `ssh_tunnel_user.sh` again with the new one. The script adds keys; it does not replace the old ones). Database host `127.0.0.1`, port 3306, user `fivetran`. Update method: binary log (log-based). Tables: `customers`, `order_reviews`.

### 4.4 Sync frequency

Set both connectors to **every 6 hours** for now (you trigger syncs yourself during the demo; this protects the row limit). Record it in `docs/evidence/s2-04-fivetran-notes.md` with your plan name, region and the IP list you used.

### 4.5 Look at Bronze

```powershell
python scripts/check_snowflake.py
```

Expected schemas `PG_PUBLIC` and `MYSQL_CRM`, with `PRODUCTS`, `SELLERS`, `CATEGORY_TRANSLATION`, `CUSTOMERS`, `ORDER_REVIEWS` and row counts near the source (products about 32,951 plus anything the simulator added, and so on). **If the schema names differ**, put the real names into `.env` as `BRONZE_SCHEMA_POSTGRES` and `BRONZE_SCHEMA_MYSQL`, and into `dbt/klarity/dbt_project.yml` under `vars`.

Also open Fivetran's usage page and write down the monthly active rows used so far.

**Gate 2:** PostgreSQL and MySQL tables are in Bronze with counts that match the source.

---

## 5. Oracle (S2-06): decide, then build

**Deadline for the decision: end of the first Fivetran test.** Spend at most 45 minutes on option A.

**Option A: Fivetran's Oracle connector.** Add connector, Oracle, schema prefix `oracle` (should give `ORACLE_KLARITY_APP`), SSH tunnel to `127.0.0.1:1521`, service `XEPDB1`, user `klarity_ro`. It may refuse the plan, or fail because of Oracle XE and logging (ARCHIVELOG). If it will not save, **stop** and go to option B.

**Option B (fallback): Python loader.** Needs your mentor's OK in writing (one line is enough) and a short ADR. Copy this into `docs/adr/0006-oracle-ingestion-fallback.md`:

```
# ADR 0006: Oracle ingestion without Fivetran
Status: proposed. Date: 16 Nov 2026.
Context: Fivetran's Oracle connector is not available on the Free plan / does not support Oracle XE (see docs/evidence/s2-04-fivetran-notes.md).
Decision: a Python loader (sources/load_oracle_to_snowflake.py) copies orders, order_items and order_payments into BRONZE.ORACLE_KLARITY_APP as a full refresh, with the same table names and the Fivetran columns.
Consequences: no log-based change capture; deletes and updates are picked up only on a full refresh; it is run by Airflow in Sprint 4. Money columns are floats at load time (reconciled with tolerance 0.01).
```

Run it from your laptop (needs Oracle reachable from your laptop: `.env.aws` with your IP allowed, as in Sprint 1, and `KLARITY_ENV_FILE` set):

```powershell
$env:KLARITY_ENV_FILE = ".env.aws"
python sources/load_oracle_to_snowflake.py
```

The row-limit bonus: the loader does not use Fivetran rows.

**Gate 3:** all three Oracle tables are in `BRONZE.ORACLE_KLARITY_APP` (by either option).

---

## 6. Reconcile Bronze against the sources (S2-08)

**Why:** "it synced" is not proof. This is the idea of `verify_load.py`, now source against Bronze.

Stop the simulator while you do this (no source changes between the sync and the check):

```powershell
$env:KLARITY_ENV_FILE = ".env.aws"
python scripts/reconcile_bronze.py --skip geolocation --out docs/evidence/s2-08-bronze-reconciliation.md
```

Expected: every line PASS (21 checks: counts, distinct keys, sums, null counts). If a line FAILs, don't edit numbers. Re-run a sync and check again; if it still fails, send me the line.

Note about `--skip geolocation`: it is expected to be skipped for now.

---

## 7. dbt and Silver (the core of this evening and tomorrow)

**What Silver does** (all verified on a small test dataset):

| Rule | Where | Why |
| --- | --- | --- |
| Remove rows Fivetran marked deleted | all `stg_` views | the source deleted them |
| Trim text, standardise city (`SAO PAULO` becomes `Sao Paulo`) and state (`sp` becomes `SP`) | `stg_customers`, `stg_sellers` | simulator's mixed-case dirt |
| Pad zip prefixes to 5 digits | `stg_` for customers, sellers | leading zeros were lost in the CSV |
| Rename `lenght` to `length` | `stg_products` | the typo is fixed in Silver, not at the source |
| Missing category becomes `unknown`; English name added; weight 0 becomes null | `slv_products` | clean product dimension |
| Orders with no customer in MySQL are rejected (`orphan_customer`) | `rej_orders` | cannot link to a customer |
| Delivered before purchased is rejected (`impossible_timeline`) | `rej_orders` | impossible data |
| Negative or null price is rejected (`invalid_price`) | `rej_order_items` | wrong money |
| Items and payments of rejected orders are rejected (`order_not_in_silver`) | `rej_order_items`, `rej_order_payments` | keep the tables consistent |
| Review score outside 1 to 5 is rejected (`invalid_score`) | `rej_reviews` | impossible score |
| Same review twice for one order: keep the newest (`duplicate_review`) | `rej_reviews` | one review per order and review id |
| Review whose order was deleted or rejected is rejected (`order_not_in_silver`) | `rej_reviews` | the cross-system orphan |
| All rejected rows are listed with the reason | `slv_quarantine` | nothing disappears silently |
| Warnings that keep the row (no estimated date, order without items, unknown product or seller, missing category) | `slv_dq_flags` | visible on the Data Health page |

Rows removed from Silver are never lost: they stay in Bronze and in `slv_quarantine`.

### 7.1 Install dbt in its own environment

```powershell
python -m venv .venv-dbt
.venv-dbt\Scripts\Activate.ps1
pip install -r requirements-dbt.txt
pip install python-dotenv
python scripts/run_dbt.py debug
```

Expected: `All checks passed!` at the end. (`run_dbt.py` loads your `.env` for you; dbt does not.)

### 7.2 Build and test

```powershell
python scripts/run_dbt.py build
```

This builds the 9 staging views, the Silver tables and the quarantine table, and runs about 40 tests. Time: a few minutes on the XS warehouse.

**If the first run fails**, the most likely causes are:

| Message | Fix |
| --- | --- |
| `Object 'BRONZE.PG_PUBLIC.PRODUCTS' does not exist or not authorized` | wrong schema name: use `check_snowflake.py` and fix the `vars` in `dbt_project.yml`; or the table is not synced yet |
| `invalid identifier '_FIVETRAN_DELETED'` | the soft-delete column is missing: send me the table's columns (`DESC TABLE ...`) |
| `Insufficient privileges` on BRONZE | rerun the grants in `s2_setup.sql` section 5 |
| A test fails | read which one; see 7.3 |

### 7.3 Understand failures (they are the point)

A failing test in Silver means dirty data reached Silver, or a rule is missing. Run one test at a time with `python scripts/run_dbt.py test --select slv_orders` and send me the output if you can't explain it. Do not weaken a test to make it pass.

### 7.4 Prove the quarantine caught the simulator's dirt

```powershell
$env:KLARITY_ENV_FILE = ".env.aws"
python scripts/check_quarantine_vs_log.py --log logs/change_log_aws.jsonl --out docs/evidence/s2-silver-quarantine-check.md
```

It compares what the simulator injected (negative prices, orphan orders, impossible timelines, bad scores, duplicate reviews) with what `slv_quarantine` holds. Rule: quarantined at least as many as injected (the original data has a few bad rows too). If an entry FAILs, the change has not been synced yet: run the Fivetran sync (and the Oracle loader if you use it), then `run_dbt.py build` again.

Useful queries for the demo (Snowsight, role TRANSFORMER, database SILVER):

```sql
SELECT source_table, reason_code, COUNT(*) FROM SILVER.CORE.SLV_QUARANTINE GROUP BY 1, 2 ORDER BY 1, 3 DESC;
SELECT flag, COUNT(*) FROM SILVER.CORE.SLV_DQ_FLAGS GROUP BY 1;
SELECT city, state, zip_code_prefix FROM SILVER.CORE.SLV_CUSTOMERS LIMIT 10;
```

**Gate 4 (Silver done):** `run_dbt.py build` ends with no failures, the quarantine check passes, and evidence files are saved.

---

## 8. Commit, PR, board

```powershell
git add docs dbt scripts sources infra
git status                          # no secrets
git commit -m "feat: Bronze sync evidence, Silver layer, quarantine, tests"
git push
gh pr create --title "feat: Bronze and Silver (S2-01 to S2-08)" --body "Snowflake setup, Fivetran PostgreSQL and MySQL, Oracle ingestion, reconciliation, dbt Silver layer with quarantine and tests. Closes #<S2-01>, ... "
```

Squash and merge after CI passes. Move the S2 cards to Done as the evidence exists. S2-06 is Done only after the Oracle option is decided and loaded. S2-09 (changes through to Bronze) and S2-10 (schema drift) come after Silver, per the plan.

**Cost note, every evening:** Snowsight, Admin, Cost Management: credits used. Fivetran: usage page. Stop the EC2 server when you stop for the night (`aws_host.py stop`) **only after** the day's syncs finish (Fivetran can't sync a stopped server).

---

## 9. Gates and what to cut

| Gate | Evidence | If it is late |
| --- | --- | --- |
| 1 Snowflake login works | `check_snowflake.py` output | nothing else can start; fix first |
| 2 PostgreSQL and MySQL in Bronze | `check_snowflake.py` counts | keep going with what synced |
| 3 Oracle in Bronze | same | use the fallback loader; do not wait on Fivetran |
| 4 Silver builds and tests pass | `run_dbt.py build` | cut `slv_dq_flags` tests first, never the quarantine |

**Cuts, in order, if time runs out:** geolocation (already out), SCD2, data-health page, schema drift test. Silver itself stays.

## 10. What to send me when you finish (or get stuck)

- The last 15 lines of any failing command, with no passwords.
- Which Fivetran plan name you see, the Oracle result (A or B), and the usage number.
- Whether Gates 1 to 4 passed.

Tomorrow's step after Gate 4: Gold (star schema, KPIs) and the dashboard.

---

Sources used for the facts in Part 0: [Fivetran Snowflake destination setup](https://www.fivetran.com/docs/destinations/snowflake/setup-guide), [Fivetran PostgreSQL setup guide](https://fivetran.com/docs/connectors/databases/postgresql/setup-guide), [Fivetran MySQL setup guide](https://fivetran.com/docs/connectors/databases/mysql/setup-guide), [Fivetran SSH tunnel](https://fivetran.com/docs/connectors/databases/connection-options/ssh-tunnel), [Fivetran IP addresses](https://fivetran.com/docs/security-and-privacy/ips).
