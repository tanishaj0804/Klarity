-- MySQL 8 (database crm): customers, order_reviews
-- Re-runnable: drops and recreates the two tables.

DROP TABLE IF EXISTS order_reviews;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id               CHAR(32)     NOT NULL,   -- one per order, not per person
    customer_unique_id        CHAR(32)     NOT NULL,   -- the real person
    customer_zip_code_prefix  VARCHAR(5),              -- as in the CSV (leading zeros already lost)
    customer_city             VARCHAR(64),
    customer_state            CHAR(2),
    PRIMARY KEY (customer_id),
    KEY ix_customers_unique (customer_unique_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- review_id is NOT unique in the Olist data, so a surrogate key is the primary key.
CREATE TABLE order_reviews (
    review_pk                 BIGINT       NOT NULL AUTO_INCREMENT,
    review_id                 CHAR(32)     NOT NULL,
    order_id                  CHAR(32)     NOT NULL,   -- logical link to Oracle orders
    review_score              TINYINT,
    review_comment_title      VARCHAR(255),
    review_comment_message    TEXT,
    review_creation_date      DATETIME,
    review_answer_timestamp   DATETIME,
    PRIMARY KEY (review_pk),
    KEY ix_reviews_review (review_id),
    KEY ix_reviews_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
