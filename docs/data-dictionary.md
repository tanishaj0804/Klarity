# Data dictionary: Olist Brazilian e-commerce dataset

Source: [Kaggle, Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
Nine CSV files, about 100k orders from 2016 to 2018. Real data, anonymised.
Row counts below are the commonly reported figures. Confirm yours with
`scripts/inspect_csvs.py` and correct this file if they differ.

## Where each table lives in Klarity

| CSV file | Klarity table | Database | Rows (approx.) |
| --- | --- | --- | --- |
| olist_orders_dataset.csv | orders | Oracle | 99,441 |
| olist_order_items_dataset.csv | order_items | Oracle | 112,650 |
| olist_order_payments_dataset.csv | order_payments | Oracle | 103,886 |
| olist_customers_dataset.csv | customers | MySQL | 99,441 |
| olist_order_reviews_dataset.csv | order_reviews | MySQL | 99,224 |
| olist_products_dataset.csv | products | PostgreSQL | 32,951 |
| olist_sellers_dataset.csv | sellers | PostgreSQL | 3,095 |
| product_category_name_translation.csv | category_translation | PostgreSQL | 71 |
| olist_geolocation_dataset.csv | geolocation | PostgreSQL | 1,000,163 |


## Keys and grain

| Table | Grain (one row is...) | Key |
| --- | --- | --- |
| orders | one order | order_id |
| order_items | one product line in an order | order_id + order_item_id |
| order_payments | one payment in an order | order_id + payment_sequential |
| customers | one customer record per order | customer_id |
| order_reviews | one review | surrogate review_pk (review_id repeats) |
| products | one product | product_id |
| sellers | one seller | seller_id |
| category_translation | one Portuguese category | product_category_name |
| geolocation | one coordinate sample | surrogate geolocation_id |

Key point: `customer_id` is created per order. The same person has several `customer_id`
values but one `customer_unique_id`. Customer analytics (repeat rate, cohorts, LTV) must
use `customer_unique_id`.

## orders (Oracle)

| Column | Type | Description | Notes |
| --- | --- | --- | --- |
| order_id | VARCHAR2(32) | Order identifier | Primary key |
| customer_id | VARCHAR2(32) | Customer record for this order | Links to MySQL customers |
| order_status | VARCHAR2(20) | Order state | delivered, shipped, canceled, unavailable, invoiced, processing, created, approved |
| order_purchase_timestamp | TIMESTAMP | Customer placed the order | |
| order_approved_at | TIMESTAMP | Payment approved | Some nulls |
| order_delivered_carrier_date | TIMESTAMP | Handed to the carrier | Some nulls |
| order_delivered_customer_date | TIMESTAMP | Reached the customer | Null unless delivered, a few delivered orders also null |
| order_estimated_delivery_date | TIMESTAMP | Promised delivery date | Used for on-time rate |

## order_items (Oracle)

| Column | Type | Description | Notes |
| --- | --- | --- | --- |
| order_id | VARCHAR2(32) | Order | Foreign key to orders |
| order_item_id | NUMBER(3) | Line number within the order | 1, 2, 3... |
| product_id | VARCHAR2(32) | Product sold | Links to PostgreSQL products |
| seller_id | VARCHAR2(32) | Seller | Links to PostgreSQL sellers |
| shipping_limit_date | TIMESTAMP | Seller's deadline to hand to the carrier | |
| price | NUMBER(10,2) | Item price in BRL | |
| freight_value | NUMBER(10,2) | Shipping cost for this line in BRL | |

## order_payments (Oracle)

| Column | Type | Description | Notes |
| --- | --- | --- | --- |
| order_id | VARCHAR2(32) | Order | Foreign key to orders |
| payment_sequential | NUMBER(3) | Payment number (an order can use several methods) | |
| payment_type | VARCHAR2(20) | Method | credit_card, boleto, voucher, debit_card, not_defined |
| payment_installments | NUMBER(3) | Number of instalments | |
| payment_value | NUMBER(10,2) | Amount in BRL | |

## customers (MySQL)

| Column | Type | Description | Notes |
| --- | --- | --- | --- |
| customer_id | CHAR(32) | Customer record, one per order | Primary key |
| customer_unique_id | CHAR(32) | The real person | Fewer distinct values than customer_id |
| customer_zip_code_prefix | VARCHAR(5) | First five digits of the zip code | Kept as text. Leading zeros are already lost in the CSV. Pad to 5 in Silver |
| customer_city | VARCHAR(64) | City | Lowercase, accents removed in the source |
| customer_state | CHAR(2) | Brazilian state code | |

## order_reviews (MySQL)

| Column | Type | Description | Notes |
| --- | --- | --- | --- |
| review_pk | BIGINT | Surrogate key added by Klarity | Auto-increment |
| review_id | CHAR(32) | Review identifier | Not unique in the source |
| order_id | CHAR(32) | Reviewed order | Links to Oracle orders |
| review_score | TINYINT | 1 (worst) to 5 (best) | |
| review_comment_title | VARCHAR(255) | Optional title | Mostly empty |
| review_comment_message | TEXT | Optional comment in Portuguese | Mostly empty, may contain line breaks |
| review_creation_date | DATETIME | Survey sent | |
| review_answer_timestamp | DATETIME | Customer answered | |

## products (PostgreSQL)

| Column | Type | Description | Notes |
| --- | --- | --- | --- |
| product_id | VARCHAR(32) | Product | Primary key |
| product_category_name | VARCHAR(80) | Category in Portuguese | Some nulls |
| product_name_lenght | INTEGER | Characters in the product name | Source misspelling kept |
| product_description_lenght | INTEGER | Characters in the description | Source misspelling kept |
| product_photos_qty | INTEGER | Number of photos | |
| product_weight_g | INTEGER | Weight in grams | |
| product_length_cm | INTEGER | Length in cm | |
| product_height_cm | INTEGER | Height in cm | |
| product_width_cm | INTEGER | Width in cm | |

## sellers (PostgreSQL)

| Column | Type | Description | Notes |
| --- | --- | --- | --- |
| seller_id | VARCHAR(32) | Seller | Primary key |
| seller_zip_code_prefix | VARCHAR(5) | Zip code prefix | Same zero-padding note as customers |
| seller_city | VARCHAR(64) | City | Source has inconsistent spellings |
| seller_state | CHAR(2) | State code | |

## category_translation (PostgreSQL)

| Column | Type | Description |
| --- | --- | --- |
| product_category_name | VARCHAR(80) | Portuguese category, primary key |
| product_category_name_english | VARCHAR(80) | English category |

## geolocation (PostgreSQL)

| Column | Type | Description | Notes |
| --- | --- | --- | --- |
| geolocation_id | BIGINT | Surrogate key added by Klarity | Identity column |
| geolocation_zip_code_prefix | VARCHAR(5) | Zip code prefix | Many rows per prefix |
| geolocation_lat | DOUBLE PRECISION | Latitude | |
| geolocation_lng | DOUBLE PRECISION | Longitude | |
| geolocation_city | VARCHAR(64) | City | Spelling varies |
| geolocation_state | CHAR(2) | State code | |

Silver should collapse geolocation to one row per zip prefix (average lat/lng) before
computing distances.

## Known quirks in the raw data (expected, to be confirmed in S1-11)

| Quirk | Effect |
| --- | --- |
| Same `review_id` on several rows | Deduplicate reviews in Silver, with a stated rule (latest answer wins) |
| Orders without items (mostly canceled or unavailable) | Left join, not inner join |
| A few delivered orders with no delivered date | Quarantine, do not count as on time |
| Products with no category | Show as "unknown" in Gold |
| Categories missing from the translation table | Fall back to the Portuguese name |
| Geolocation has many rows per zip prefix | Aggregate before joining |
| Zip prefixes lost leading zeros | Pad in Silver, never rely on numeric type |
| Review comments contain line breaks and accents | CSV parsing must handle quotes and UTF-8 |

## Design decisions

| Decision | Reason |
| --- | --- |
| Source column names kept as in the CSV, including "lenght" | Bronze is an exact copy. Silver renames |
| Surrogate keys on reviews and geolocation | Fivetran syncs cleanly when every table has a primary key |
| Foreign keys only inside Oracle | Cross-database links cannot be enforced, which is the real-world situation the project simulates |
| No CHECK constraints (for example on price) | The simulator injects negative prices and mixed-case text on purpose in S1-10 |
