# ADR 0005: EC2 hosts all three source databases (no RDS)

- **Status:** proposed (set to `accepted` once the mentor agrees)
- **Date:** 11 Nov 2026
- **Affects stories:** S1-06, S1-07, S1-08

## Context
The README planned Oracle and MySQL on EC2 and PostgreSQL on RDS. Sprint 1 found:
- The same Docker containers already run and are verified on the laptop.
- The AWS account is on the Free plan; money must not be spent. A separate RDS instance is one more running resource, and a stopped RDS instance restarts itself after 7 days.
- Fivetran only needs a reachable PostgreSQL with logical replication; it does not care whether it is RDS.
- The mentor said local databases are acceptable if AWS billing is a problem.

## Decision
1. One EC2 instance (x86, Free-plan eligible, 4 to 8 GB) runs Oracle XE, MySQL 8 and PostgreSQL 16 in Docker (`infra/aws/docker-compose.yml`).
2. PostgreSQL is started with `wal_level=logical`, which is what Fivetran needs.
3. S1-07 is delivered as "PostgreSQL on the same EC2 server".
4. Local Docker stays as the development copy. A `.env.*` file selects the target (`KLARITY_ENV_FILE`).
5. The firewall allows only registered laptop IPs, one rule label per laptop.

## Consequences
- Cheaper and simpler; identical to the local setup.
- No managed backups, patching or failover. Acceptable for a learning project with reloadable data.
- The server is one point of failure. Recovery is `docker compose up -d` plus `load_olist.py --reload`.
- RDS can be added later by changing `PG_HOST` only. A move would need a new ADR.
- Any Python loader that replaces Fivetran for Oracle (Fivetran's Oracle connector may not support XE) needs its own ADR and mentor approval.
