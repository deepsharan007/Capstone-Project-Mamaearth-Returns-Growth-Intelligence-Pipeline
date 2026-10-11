-- =====================================================================
-- sql/schema.sql  |  Part 1, Task 1  |  Mamaearth Returns Pipeline
-- Creates the 3 tables. Safe to re-run: old tables are dropped first.
-- =====================================================================

PRAGMA foreign_keys = ON;   -- SQLite only enforces FOREIGN KEYs when this is ON

-- Drop child table first (orders points at customers & products)
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;

CREATE TABLE customers (
    customer_id        VARCHAR(10) PRIMARY KEY,
    name               VARCHAR(50) NOT NULL,
    city               VARCHAR(50) NOT NULL,
    city_tier          INT         NOT NULL,
    signup_date        DATE        NOT NULL,
    acquisition_source VARCHAR(20) NOT NULL
);

CREATE TABLE products (
    product_id   VARCHAR(10)   PRIMARY KEY,
    product_name VARCHAR(100)  NOT NULL,
    category     VARCHAR(30)   NOT NULL,
    price        DECIMAL(10,2) NOT NULL
);

CREATE TABLE orders (
    order_id       VARCHAR(10) PRIMARY KEY,
    customer_id    VARCHAR(10) NOT NULL,
    product_id     VARCHAR(10) NOT NULL,
    order_date     DATE        NOT NULL,
    quantity       INT         NOT NULL,
    discount_pct   INT,                       -- nullable on purpose: no promo code = NULL
    payment_method VARCHAR(10) NOT NULL,
    rating         INT,                       -- nullable on purpose: not yet rated = NULL
    returned       INT         NOT NULL DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id)  REFERENCES products(product_id)
);
