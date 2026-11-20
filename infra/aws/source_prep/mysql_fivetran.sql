-- MySQL 8 (database crm): prepare for Fivetran (story S2-03 / S2-05).
-- Run inside the mysql container as root:
--   sudo docker exec -i klarity-mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD"' < mysql_fivetran.sql
-- Replace CHANGE_ME with a new strong password (store it in your password manager).

CREATE USER IF NOT EXISTS 'fivetran'@'%' IDENTIFIED WITH mysql_native_password BY 'CHANGE_ME';
GRANT SELECT, REPLICATION CLIENT, REPLICATION SLAVE ON *.* TO 'fivetran'@'%';
FLUSH PRIVILEGES;

-- Checks. Fivetran's guide wants binary logging on and row format.
-- MySQL 8 normally has these by default; if any value differs, tell me.
SHOW VARIABLES WHERE Variable_name IN ('log_bin', 'binlog_format', 'binlog_row_image', 'server_id',
                                       'binlog_expire_logs_seconds');
SHOW GRANTS FOR 'fivetran'@'%';
