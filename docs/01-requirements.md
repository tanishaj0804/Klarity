# Requirements

## Business questions

1. What is revenue by month and by product category?
2. Which categories and products sell the most?
3. Which sellers deliver late, and how late?
4. What is the average review score by category and seller?
5. How many new customers per month, and where are they?

## KPIs

| KPI | Definition | Grain |
| --- | --- | --- |
| Revenue | sum(price + freight) of delivered order items | order item |
| Average order value | revenue / distinct orders | order |
| On-time delivery rate | delivered on or before the estimate / delivered | order |
| Average review score | mean of review_score | review |

## Non-functional requirements

- Refresh nightly, alert if Bronze is older than 24 hours
- Dashboard reads only the Gold layer through a read-only role
- No credentials in code or Git
- Everything rebuildable from Bronze
- Low cost: budget alerts, auto-suspend, stop idle servers

## Mentor approval

- Status: pending
- Date:
- Notes:
