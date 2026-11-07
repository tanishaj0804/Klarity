-- Oracle XE (service XEPDB1): orders, order_items, order_payments
-- Run as the app user (klarity_app). Safe to re-run: uncomment the DROP block first.
--
-- DROP TABLE order_payments PURGE;
-- DROP TABLE order_items PURGE;
-- DROP TABLE orders PURGE;

CREATE TABLE orders (
    order_id                       VARCHAR2(32)  NOT NULL,
    customer_id                    VARCHAR2(32)  NOT NULL,  -- logical link to MySQL customers
    order_status                   VARCHAR2(20),
    order_purchase_timestamp       TIMESTAMP,
    order_approved_at              TIMESTAMP,
    order_delivered_carrier_date   TIMESTAMP,
    order_delivered_customer_date  TIMESTAMP,
    order_estimated_delivery_date  TIMESTAMP,
    CONSTRAINT pk_orders PRIMARY KEY (order_id)
);

CREATE TABLE order_items (
    order_id             VARCHAR2(32)  NOT NULL,
    order_item_id        NUMBER(3)     NOT NULL,
    product_id           VARCHAR2(32)  NOT NULL,  -- logical link to PostgreSQL products
    seller_id            VARCHAR2(32)  NOT NULL,  -- logical link to PostgreSQL sellers
    shipping_limit_date  TIMESTAMP,
    price                NUMBER(10, 2),
    freight_value        NUMBER(10, 2),
    CONSTRAINT pk_order_items PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

CREATE TABLE order_payments (
    order_id              VARCHAR2(32)  NOT NULL,
    payment_sequential    NUMBER(3)     NOT NULL,
    payment_type          VARCHAR2(20),
    payment_installments  NUMBER(3),
    payment_value         NUMBER(10, 2),
    CONSTRAINT pk_order_payments PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_order_payments_order FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

CREATE INDEX ix_orders_customer ON orders (customer_id);
CREATE INDEX ix_order_items_product ON order_items (product_id);
CREATE INDEX ix_order_items_seller ON order_items (seller_id);
