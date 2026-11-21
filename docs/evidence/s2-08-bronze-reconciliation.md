| system   | table                | check                               | source      | bronze             | result |
|----------|----------------------|-------------------------------------|-------------|--------------------|--------|
| oracle   | orders               | rows                                | 99834       | 99834              | PASS   |
| oracle   | orders               | distinct order_id                   | 99834       | 99834              | PASS   |
| oracle   | orders               | nulls order_approved_at             | 276         | 276                | PASS   |
| oracle   | orders               | nulls order_delivered_customer_date | 3343        | 3343               | PASS   |
| oracle   | order_items          | rows                                | 113402      | 113402             | PASS   |
| oracle   | order_items          | sum price                           | 13663905.25 | 13663905.25        | PASS   |
| oracle   | order_items          | sum freight_value                   | 2271166.19  | 2271166.1900000004 | PASS   |
| oracle   | order_items          | distinct product_id                 | 32951       | 32951              | PASS   |
| oracle   | order_payments       | rows                                | 104265      | 104265             | PASS   |
| oracle   | order_payments       | sum payment_value                   | 16102600.28 | 16102600.28        | PASS   |
| mysql    | customers            | rows                                | 99827       | 99827              | PASS   |
| mysql    | customers            | distinct customer_unique_id         | 96358       | 96358              | PASS   |
| mysql    | order_reviews        | rows                                | 99246       | 99246              | PASS   |
| mysql    | order_reviews        | distinct review_id                  | 98418       | 98418              | PASS   |
| mysql    | order_reviews        | sum review_score                    | 405535      | 405535             | PASS   |
| postgres | products             | rows                                | 32951       | 32951              | PASS   |
| postgres | products             | nulls product_category_name         | 610         | 610                | PASS   |
| postgres | products             | sum product_weight_g                | 75007492    | 75007492           | PASS   |
| postgres | sellers              | rows                                | 3095        | 3095               | PASS   |
| postgres | sellers              | distinct seller_state               | 23          | 23                 | PASS   |
| postgres | category_translation | rows                                | 71          | 71                 | PASS   |

21 passed, 0 failed
