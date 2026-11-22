| system   | table                | check                               | source      | bronze             | result |
|----------|----------------------|-------------------------------------|-------------|--------------------|--------|
| oracle   | orders               | rows                                | 99883       | 99883              | PASS   |
| oracle   | orders               | distinct order_id                   | 99883       | 99883              | PASS   |
| oracle   | orders               | nulls order_approved_at             | 294         | 294                | PASS   |
| oracle   | orders               | nulls order_delivered_customer_date | 3389        | 3389               | PASS   |
| oracle   | order_items          | rows                                | 113488      | 113488             | PASS   |
| oracle   | order_items          | sum price                           | 13672516.1  | 13672516.100000001 | PASS   |
| oracle   | order_items          | sum freight_value                   | 2273284.54  | 2273284.54         | PASS   |
| oracle   | order_items          | distinct product_id                 | 32951       | 32951              | PASS   |
| oracle   | order_payments       | rows                                | 104312      | 104312             | PASS   |
| oracle   | order_payments       | sum payment_value                   | 16113485.74 | 16113485.739999998 | PASS   |
| mysql    | customers            | rows                                | 99875       | 99875              | PASS   |
| mysql    | customers            | distinct customer_unique_id         | 96393       | 96393              | PASS   |
| mysql    | order_reviews        | rows                                | 99250       | 99250              | PASS   |
| mysql    | order_reviews        | distinct review_id                  | 98420       | 98420              | PASS   |
| mysql    | order_reviews        | sum review_score                    | 405544      | 405544             | PASS   |
| postgres | products             | rows                                | 32951       | 32951              | PASS   |
| postgres | products             | nulls product_category_name         | 610         | 610                | PASS   |
| postgres | products             | sum product_weight_g                | 75007492    | 75007492           | PASS   |
| postgres | sellers              | rows                                | 3095        | 3095               | PASS   |
| postgres | sellers              | distinct seller_state               | 23          | 23                 | PASS   |
| postgres | category_translation | rows                                | 71          | 71                 | PASS   |

21 passed, 0 failed
