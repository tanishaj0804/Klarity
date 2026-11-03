-- Sprint 2. Run as ACCOUNTADMIN.
create warehouse if not exists wh_xs
  warehouse_size = 'XSMALL'
  auto_suspend = 60
  auto_resume = true;

create database if not exists bronze;
create database if not exists silver;
create database if not exists gold;

-- resource monitor: set the credit quota when you create the account
-- create resource monitor ...
