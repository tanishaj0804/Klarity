# ER diagram

Solid lines are real foreign keys inside one database. Dotted lines are logical links
across databases: no database enforces them, so orphans can exist. Silver and Gold
must check them. Key columns only; see `data-dictionary.md` for every column.

```mermaid
erDiagram
  customers {
    char customer_id PK
    char customer_unique_id
    varchar customer_zip_code_prefix
    varchar customer_city
    char customer_state
  }
  orders {
    varchar order_id PK
    varchar customer_id
    varchar order_status
    timestamp order_purchase_timestamp
    timestamp order_delivered_customer_date
    timestamp order_estimated_delivery_date
  }
  order_items {
    varchar order_id PK
    number order_item_id PK
    varchar product_id
    varchar seller_id
    number price
    number freight_value
  }
  order_payments {
    varchar order_id PK
    number payment_sequential PK
    varchar payment_type
    number payment_installments
    number payment_value
  }
  order_reviews {
    bigint review_pk PK
    char review_id
    char order_id
    tinyint review_score
  }
  products {
    varchar product_id PK
    varchar product_category_name
    integer product_weight_g
  }
  sellers {
    varchar seller_id PK
    varchar seller_zip_code_prefix
    varchar seller_state
  }
  category_translation {
    varchar product_category_name PK
    varchar product_category_name_english
  }
  geolocation {
    bigint geolocation_id PK
    varchar geolocation_zip_code_prefix
    double geolocation_lat
    double geolocation_lng
  }

  orders ||--|{ order_items : contains
  orders ||--o{ order_payments : "paid by"
  customers ||..o{ orders : places
  orders ||..o{ order_reviews : "reviewed in"
  products ||..o{ order_items : "sold as"
  sellers ||..o{ order_items : "sold by"
  category_translation ||..o{ products : translates
  geolocation }o..o{ customers : "zip prefix"
  geolocation }o..o{ sellers : "zip prefix"
```

## Which database holds what

| Database | Tables | Why |
| --- | --- | --- |
| Oracle XE (EC2, Docker) | orders, order_items, order_payments | Transactions: the "ERP" |
| MySQL 8 (EC2, Docker) | customers, order_reviews | Customer-facing system: the "CRM" |
| PostgreSQL (AWS RDS) | products, sellers, category_translation, geolocation | Catalogue and reference data |

## Logical links across databases

| From | To | Join |
| --- | --- | --- |
| Oracle `orders.customer_id` | MySQL `customers.customer_id` | equality |
| Oracle `order_items.product_id` | PostgreSQL `products.product_id` | equality |
| Oracle `order_items.seller_id` | PostgreSQL `sellers.seller_id` | equality |
| MySQL `order_reviews.order_id` | Oracle `orders.order_id` | equality |
| PostgreSQL `products.product_category_name` | PostgreSQL `category_translation` | equality |
| MySQL `customers` / PostgreSQL `sellers` | PostgreSQL `geolocation` | zip code prefix (many rows per prefix) |
