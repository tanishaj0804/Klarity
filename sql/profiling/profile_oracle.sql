-- Profiling queries for oracle. Each returns the number of rows affected.

-- 2. Orders without any items
SELECT COUNT(*) FROM orders o LEFT JOIN order_items i ON i.order_id = o.order_id WHERE i.order_id IS NULL;

-- 3. Delivered orders with no delivery date
SELECT COUNT(*) FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL;

-- A. Negative or zero item price
SELECT COUNT(*) FROM order_items WHERE price <= 0;

-- B. Delivered before purchased
SELECT COUNT(*) FROM orders WHERE order_delivered_customer_date < order_purchase_timestamp;

-- C. Order with no estimated delivery date
SELECT COUNT(*) FROM orders WHERE order_estimated_delivery_date IS NULL;
