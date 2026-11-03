# ADR 0002: Bronze / Silver / Gold layers

Status: accepted

Bronze is a raw copy from Fivetran, Silver is cleaned by dbt, Gold is the star schema for
dashboards. Dashboards read Gold only. Everything can be rebuilt from Bronze.
