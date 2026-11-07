# Requirements (v2, revised after mentor feedback, 4 Nov 2026)

Version 1 had 5 questions and 4 KPIs. The mentor asked for deeper KPIs, a near-real-time
reporting layer, and visibly non-trivial transformations. This version adds them.
Status: **awaiting mentor approval**.

## Business questions

### Core
1. What is revenue by month and category, and how fast is it growing (MoM, YoY, 3-month moving average)?
2. Which categories and products drive the most revenue, and how concentrated is revenue (Pareto)?
3. Which sellers deliver late, how late, and where in the journey is the delay?
4. How does delivery delay affect review scores, by category and seller?
5. How many new customers per month, where are they, and do they come back?

### Advanced
6. Do customers return? Show cohort retention by first-order month.
7. What is customer lifetime value by cohort, and who are the top customer segments (RFM)?
8. Which sellers should be rewarded or put on watch (scorecard with a tier)?
9. How do payment method and instalments affect order value and cancellations?
10. Is the platform data healthy right now (freshness, reconciliation, quality)?

## KPIs

### Tier 1: Business KPIs

| KPI | Definition | Grain |
| --- | --- | --- |
| GMV | sum(price + freight) of all non-cancelled order items | order item |
| Net revenue | sum(price) of delivered order items, excluding freight | order item |
| Average order value | net revenue / distinct delivered orders | order |
| Revenue growth | MoM and YoY change in net revenue, plus 3-month moving average | month |
| Cancellation rate | cancelled or unavailable orders / all orders | order |
| Freight ratio | freight / price, by state and category | order item |
| Average instalments | mean payment_installments, by payment type | payment |

### Tier 2: Customer KPIs

| KPI | Definition | Grain |
| --- | --- | --- |
| New customers | customers whose first order is in the month (keyed on customer_unique_id) | month |
| Repeat purchase rate | customers with 2+ orders / customers with 1+ orders | customer |
| Cohort retention | share of a first-order-month cohort that orders again in month N | cohort x month |
| Cohort LTV | cumulative net revenue per customer in a cohort at month N | cohort x month |
| RFM segment | recency, frequency, monetary quintiles (NTILE 5) mapped to segments | customer |

### Tier 3: Operations and seller KPIs

| KPI | Definition | Grain |
| --- | --- | --- |
| On-time delivery rate | delivered on or before the estimated date / delivered | order |
| Delay days (P50, P90) | days between estimated and actual delivery, late orders only | order |
| Lead-time breakdown | purchase to approval, approval to carrier, carrier to customer | order |
| Delay vs review | average review score by delay bucket (on time, 1-3, 4-7, 8+ days) | order |
| Seller scorecard | on-time rate, average review, cancellation rate, revenue share, tier (Gold, Standard, Watch) | seller |
| Seller concentration | share of revenue from top 20 percent of sellers | seller |
| Seller-customer distance | haversine distance from zip-prefix coordinates, vs delivery time | order |

### Tier 4: Pipeline health KPIs (the "Data Health" page)

| KPI | Definition |
| --- | --- |
| Data freshness | minutes since latest `_fivetran_synced` per source |
| Reconciliation pass rate | tables where source and Bronze row counts match / all tables |
| Test pass rate | passing dbt tests / all dbt tests |
| Quarantined rows | rows rejected by quality rules, by reason code |
| Pipeline run time and success | last 30 nightly runs |

## Reporting layer: near real time

- Simulator (`daily_changes.py`) can run every N minutes, not only daily.
- Fivetran syncs at the shortest interval the plan allows (to be confirmed in Sprint 2).
- Gold KPI tables refresh incrementally. Target freshness: **15 minutes or less from source change to dashboard**, measured and shown on the Data Health page.
- This is near real time, not streaming. Real-time streaming stays out of scope.

## Advanced transformations (planned)

| # | Transformation | Where |
| --- | --- | --- |
| 1 | Deduplication with `ROW_NUMBER` / `QUALIFY` and a written survivorship rule | Silver |
| 2 | Quarantine pattern: bad rows go to a quarantine table with a reason code, not deleted | Silver |
| 3 | Handling Fivetran soft deletes and late-arriving updates (order status changes) | Silver |
| 4 | Cross-source integrity: orders (Oracle), customers (MySQL), products (PostgreSQL), orphan detection, surrogate keys | Silver and Gold |
| 5 | Order status timeline: lead-time segments from five timestamps | Gold |
| 6 | Incremental merge facts (`fct_orders`, `fct_order_items`) with a stated grain | Gold |
| 7 | SCD Type 2 on customer and seller dimensions (dbt snapshots, driven by simulated address changes) | Gold |
| 8 | Cohort retention matrix and cohort LTV with window functions | Gold |
| 9 | RFM scoring with `NTILE` | Gold |
| 10 | Percentiles (P50, P90) and Pareto ranking | Gold |
| 11 | Geo distance (haversine) from zip-prefix coordinates | Gold |
| 12 | Time zones: pipeline in UTC, reporting in America/Sao_Paulo | Gold |
| 13 | Row-level security through a REPORTER role | Snowflake |
| 14 | Data contract tests, freshness checks and reconciliation SQL | dbt and SQL |

## Dashboard pages

1. Executive overview (Tier 1)
2. Customers (Tier 2: cohorts, retention, LTV, RFM)
3. Logistics and sellers (Tier 3)
4. Data health (Tier 4, near-real-time freshness)


## Non-functional requirements

- Nightly full refresh plus intraday incremental refresh, alert if Bronze is older than 24 hours
- Dashboard reads only the Gold layer through a read-only role
- No credentials in code or Git
- Everything rebuildable from Bronze
- Low cost: budget alerts, auto-suspend, stop idle servers

## Scope

In: Olist data in three databases, Fivetran ingestion, Snowflake, dbt, Airflow, CI/CD,
one four-page dashboard, handover documents.
Out: real-time streaming, machine learning, high availability, multi-region.
