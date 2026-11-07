-- PostgreSQL (database catalog): products, sellers, category_translation, geolocation
-- Re-runnable: drops and recreates the tables.

DROP TABLE IF EXISTS geolocation;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS sellers;
DROP TABLE IF EXISTS category_translation;

CREATE TABLE category_translation (
    product_category_name          VARCHAR(80) PRIMARY KEY,
    product_category_name_english  VARCHAR(80) NOT NULL
);

-- Column names keep the source spelling ("lenght"). Silver renames them.
CREATE TABLE products (
    product_id                   VARCHAR(32) PRIMARY KEY,
    product_category_name        VARCHAR(80),
    product_name_lenght          INTEGER,
    product_description_lenght   INTEGER,
    product_photos_qty           INTEGER,
    product_weight_g             INTEGER,
    product_length_cm            INTEGER,
    product_height_cm            INTEGER,
    product_width_cm             INTEGER
);

CREATE TABLE sellers (
    seller_id                VARCHAR(32) PRIMARY KEY,
    seller_zip_code_prefix   VARCHAR(5),
    seller_city              VARCHAR(64),
    seller_state             CHAR(2)
);

-- Many rows per zip prefix in the source, so a surrogate key is the primary key.
CREATE TABLE geolocation (
    geolocation_id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    geolocation_zip_code_prefix  VARCHAR(5),
    geolocation_lat              DOUBLE PRECISION,
    geolocation_lng              DOUBLE PRECISION,
    geolocation_city             VARCHAR(64),
    geolocation_state            CHAR(2)
);

CREATE INDEX ix_products_category ON products (product_category_name);
CREATE INDEX ix_geolocation_zip ON geolocation (geolocation_zip_code_prefix);
