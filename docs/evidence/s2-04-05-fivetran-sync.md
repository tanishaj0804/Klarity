# S2-04 and S2-05: Fivetran PostgreSQL and MySQL to Bronze

Row counts: all PostgreSQL and MySQL tables match the sources, see
`docs/evidence/s2-08-bronze-reconciliation.md` (21 of 21 checks PASS).

| Connector | Bronze schema | Tables synced | Sync frequency chosen |
| --- | --- | --- | --- |
| PostgreSQL | POSTGRES_PUBLIC | products, sellers, category_translation (geolocation: not synced) | 6 hours |
| MySQL | crm (lowercase, needs quoting in SQL) | customers, order_reviews | 6 hours|
