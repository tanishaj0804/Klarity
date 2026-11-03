# Runbook

Filled in as the project progresses.

## Start and stop

- Stop EC2 when idle (nights, weekends).
- Weekly: check AWS Billing, Snowflake credits, Fivetran rows.

## Cleanup at project end

- Terminate EC2 instances, delete RDS, release Elastic IPs, delete unused volumes.
- Drop Snowflake warehouse and databases, pause Fivetran connectors.
- Write the final cost report.
