-- Profiling queries for postgres. Each returns the number of rows affected.

-- 4. Products without a category
SELECT COUNT(*) FROM products WHERE product_category_name IS NULL;

-- 5. Categories missing from the translation table
SELECT COUNT(DISTINCT p.product_category_name) FROM products p LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name WHERE p.product_category_name IS NOT NULL AND t.product_category_name IS NULL;

-- 7. Many geolocation rows per zip prefix
SELECT COUNT(*) - COUNT(DISTINCT geolocation_zip_code_prefix) FROM geolocation;
