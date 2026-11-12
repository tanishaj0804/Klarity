| system | table | check | csv/log | database | result |
| --- | --- | --- | --- | --- | --- |
| oracle | orders | rows | 99441 | 99441 | PASS |
| oracle | orders | distinct order_id | 99441 | 99441 | PASS |
| oracle | orders | min order_purchase_timestamp | 2016-09-04 21:15:19 | 2016-09-04 21:15:19 | PASS |
| oracle | orders | max order_purchase_timestamp | 2018-10-17 17:30:18 | 2018-10-17 17:30:18 | PASS |
| oracle | orders | nulls order_approved_at | 160 | 160 | PASS |
| oracle | orders | nulls order_delivered_customer_date | 2965 | 2965 | PASS |
| oracle | order_items | rows | 112650 | 112650 | PASS |
| oracle | order_items | sum price | 13591643.70 | 13591643.7 | PASS |
| oracle | order_items | sum freight_value | 2251909.54 | 2251909.54 | PASS |
| oracle | order_items | distinct product_id | 32951 | 32951 | PASS |
| oracle | order_payments | rows | 103886 | 103886 | PASS |
| oracle | order_payments | sum payment_value | 16008872.12 | 16008872.12 | PASS |
| mysql | customers | rows | 99441 | 99441 | PASS |
| mysql | customers | distinct customer_unique_id | 96096 | 96096 | PASS |
| mysql | order_reviews | rows | 99224 | 99224 | PASS |
| mysql | order_reviews | distinct review_id | 98410 | 98410 | PASS |
| mysql | order_reviews | sum review_score | 405471 | 405471 | PASS |
| postgres | products | rows | 32951 | 32951 | PASS |
| postgres | products | nulls product_category_name | 610 | 610 | PASS |
| postgres | products | sum product_weight_g | 75007492 | 75007492 | PASS |
| postgres | sellers | rows | 3095 | 3095 | PASS |
| postgres | sellers | distinct seller_state | 23 | 23 | PASS |
| postgres | category_translation | rows | 71 | 71 | PASS |
| postgres | geolocation | rows | 1000163 | 1000163 | PASS |
| postgres | geolocation | distinct geolocation_zip_code_prefix | 19015 | 19015 | PASS |
| oracle->mysql | orders | orphans customer_id not in customers | 0 | 0 | PASS |
| oracle->postgres | order_items | orphans product_id not in products | 0 | 0 | PASS |
| oracle->postgres | order_items | orphans seller_id not in sellers | 0 | 0 | PASS |
| mysql->oracle | order_reviews | orphans order_id not in orders | 0 | 0 | PASS |
| postgres->postgres | products | orphans product_category_name not in category_translation | 13 | 13 | PASS |
