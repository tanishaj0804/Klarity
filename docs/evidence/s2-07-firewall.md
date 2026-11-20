# S2-07: firewall allows only Fivetran and my IPs



| Rule label | Source | Port | Why |
| --- | --- | --- | --- |
| <home / office> | 103.5.135.107/32 | <22, 1521, 3306, 5432> | my laptop |
| fivetran | 0.0.0.0 | 22 | Fivetran SSH tunnel |

Region used for the Fivetran IP list: asia Pacific
