-- OSI Playground: Snowflake test-data setup.
--
-- Run this in the Snowflake database + schema configured in
-- .streamlit/secrets.toml (st.secrets["osi"]["database"] /
-- st.secrets["osi"]["schema"]).
--
-- Usage:
--   snowsql -q "USE DATABASE <database>; USE SCHEMA <schema>;"
--   snowsql -f setup/snowflake_setup.sql
--
-- The table and column names match the demo_orders and tpcds_thin
-- models in playground/scenarios/models/.

-- ============================================================
-- demo_orders schema
-- ============================================================

CREATE TABLE IF NOT EXISTS sales_customers (
    id              INTEGER       NOT NULL,
    email           VARCHAR(255),
    region          VARCHAR(50),
    market_segment  VARCHAR(50)
);

INSERT INTO sales_customers (id, email, region, market_segment) VALUES
    (1, 'alice@example.com', 'NA',   'enterprise'),
    (2, 'bob@example.com',   'NA',   'smb'),
    (3, 'caro@example.com',  'EMEA', 'enterprise'),
    (4, 'dan@example.com',   'APAC', 'smb');

CREATE TABLE IF NOT EXISTS sales_orders (
    order_id     INTEGER       NOT NULL,
    order_number VARCHAR(50),
    customer_id  INTEGER,
    order_date   DATE,
    status       VARCHAR(50),
    amount       FLOAT,
    discount     FLOAT
);

INSERT INTO sales_orders (order_id, order_number, customer_id, order_date, status, amount, discount) VALUES
    (10, 'ORD-010', 1, '2024-01-10', 'paid',    100.0,  5.0),
    (11, 'ORD-011', 1, '2024-01-15', 'paid',    200.0, 10.0),
    (12, 'ORD-012', 2, '2024-01-20', 'paid',     50.0,  0.0),
    (13, 'ORD-013', 2, '2024-02-01', 'pending',  75.0,  0.0),
    (14, 'ORD-014', 3, '2024-02-10', 'paid',    300.0, 15.0),
    (15, 'ORD-015', 4, '2024-02-15', 'pending', 125.0,  0.0);

CREATE TABLE IF NOT EXISTS sales_returns (
    return_id     INTEGER NOT NULL,
    customer_id   INTEGER,
    order_id      INTEGER,
    refund_amount FLOAT
);

INSERT INTO sales_returns (return_id, customer_id, order_id, refund_amount) VALUES
    (100, 1, 10, 20.0),
    (101, 3, 14, 50.0),
    (102, 4, 15, 10.0);

CREATE TABLE IF NOT EXISTS sales_line_items (
    order_id    INTEGER NOT NULL,
    line_number INTEGER NOT NULL,
    product_id  INTEGER,
    quantity    INTEGER,
    unit_price  FLOAT
);

INSERT INTO sales_line_items (order_id, line_number, product_id, quantity, unit_price) VALUES
    (10, 1, 101, 2, 50.0),
    (10, 2, 102, 1, 10.0),
    (11, 1, 103, 3, 66.67),
    (12, 1, 101, 1, 50.0),
    (13, 1, 104, 1, 75.0),
    (14, 1, 103, 2, 100.0),
    (14, 2, 105, 1, 100.0),
    (15, 1, 104, 1, 125.0);

-- ============================================================
-- tpcds_thin schema
-- ============================================================

CREATE TABLE IF NOT EXISTS tpcds_item (
    i_item_sk   INTEGER NOT NULL,
    i_category  VARCHAR(50),
    i_class     VARCHAR(50),
    i_brand     VARCHAR(50)
);

INSERT INTO tpcds_item (i_item_sk, i_category, i_class, i_brand) VALUES
    (1, 'Books',  'fiction',   'acme'),
    (2, 'Books',  'nonfic',    'acme'),
    (3, 'Music',  'pop',       'zen'),
    (4, 'Music',  'classical', 'zen'),
    (5, 'Sports', 'running',   'fit');

CREATE TABLE IF NOT EXISTS tpcds_customer (
    c_customer_sk         INTEGER NOT NULL,
    c_birth_country       VARCHAR(50),
    c_preferred_cust_flag VARCHAR(1)
);

INSERT INTO tpcds_customer (c_customer_sk, c_birth_country, c_preferred_cust_flag) VALUES
    (1, 'USA',    'Y'),
    (2, 'USA',    'N'),
    (3, 'CANADA', 'Y'),
    (4, 'MEXICO', 'N');

CREATE TABLE IF NOT EXISTS tpcds_store (
    s_store_sk INTEGER NOT NULL,
    s_state    VARCHAR(10),
    s_country  VARCHAR(50)
);

INSERT INTO tpcds_store (s_store_sk, s_state, s_country) VALUES
    (10, 'CA', 'USA'),
    (11, 'NY', 'USA'),
    (12, 'ON', 'CANADA');

CREATE TABLE IF NOT EXISTS tpcds_store_sales (
    ss_ticket_number   INTEGER NOT NULL,
    ss_item_sk         INTEGER NOT NULL,
    ss_customer_sk     INTEGER,
    ss_store_sk        INTEGER,
    ss_sold_date_sk    INTEGER,
    ss_quantity        INTEGER,
    ss_ext_sales_price FLOAT,
    ss_net_profit      FLOAT
);

INSERT INTO tpcds_store_sales VALUES
    (1001, 1, 1, 10, 20250101, 2,  20.0,  8.0),
    (1001, 3, 1, 10, 20250101, 1,  15.0,  5.0),
    (1002, 2, 2, 11, 20250102, 3,  30.0, 10.0),
    (1002, 5, 2, 11, 20250102, 1,  50.0, 20.0),
    (1003, 4, 3, 12, 20250103, 2,  40.0, 15.0),
    (1004, 1, 3, 12, 20250104, 1,  10.0,  4.0),
    (1005, 5, 4, 10, 20250105, 2, 100.0, 40.0);

CREATE TABLE IF NOT EXISTS tpcds_store_returns (
    sr_ticket_number INTEGER NOT NULL,
    sr_item_sk       INTEGER NOT NULL,
    sr_customer_sk   INTEGER,
    sr_store_sk      INTEGER,
    sr_return_amt    FLOAT
);

INSERT INTO tpcds_store_returns VALUES
    (1002, 5, 2, 11, 50.0),
    (1005, 5, 4, 10, 25.0);
