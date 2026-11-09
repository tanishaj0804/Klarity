-- Profiling queries for mysql. Each returns the number of rows affected.

-- 1. Duplicate review_id
SELECT COALESCE(SUM(c - 1), 0) FROM (SELECT review_id, COUNT(*) c FROM order_reviews GROUP BY review_id HAVING COUNT(*) > 1) d;

-- 6. One person with several customer_id values
SELECT COUNT(*) - COUNT(DISTINCT customer_unique_id) FROM customers;

-- D. Mixed-case city or state
SELECT COUNT(*) FROM customers WHERE customer_city COLLATE utf8mb4_bin <> LOWER(customer_city) OR customer_state COLLATE utf8mb4_bin <> UPPER(customer_state);

-- E. Review score outside 1 to 5
SELECT COUNT(*) FROM order_reviews WHERE review_score NOT BETWEEN 1 AND 5;
