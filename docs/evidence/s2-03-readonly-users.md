# S2-03: read-only source users

Scripts: `infra/aws/source_prep/oracle_readonly.sql`, `mysql_fivetran.sql`, `postgres_fivetran.sql`.
Passwords are stored only in .env files and the password manager (confirm: yes / no).

For each database, connect as the read-only user and run a SELECT (works) and an INSERT (refused).

| Database | User | SELECT | INSERT refused with |
| --- | --- | --- | --- |
| Oracle XEPDB1 | klarity_ro | `SELECT COUNT(*) FROM klarity_app.orders;` -> 99834 | ORA-01031 insufficient privileges |
| MySQL crm | fivetran | `SELECT COUNT(*) FROM crm.customers;` -> 99827 | ERROR 1142 INSERT command denied |
| PostgreSQL catalog | fivetran | `SELECT COUNT(*) FROM products;` -> 32951 | permission denied for table |

Commands (run inside the containers on EC2, as in each script's header):
```
sudo docker exec -it klarity-oracle sqlplus klarity_ro/<pw>@//localhost:1521/XEPDB1
sudo docker exec -it klarity-mysql mysql -ufivetran -p crm
sudo docker exec -it klarity-postgres psql -U fivetran -d catalog
```
