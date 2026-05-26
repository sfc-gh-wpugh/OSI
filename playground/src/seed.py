"""Seed an in-memory DuckDB connection with demo data.

Provides two seeding functions:

* :func:`seed_demo_orders` — ``sales.customers``, ``sales.orders``,
  ``sales.returns``, ``sales.line_items`` used by the ``demo_orders``
  playground model.
* :func:`seed_tpcds` — ``tpcds.*`` tables used by the ``tpcds_thin``
  playground model.

Extracted from:
  - ``impl/python/tests/e2e/conftest.py`` ``_seed()``
  - ``impl/python/tests/e2e/tpcds_fixtures.py`` ``seed_tpcds()``
"""

from __future__ import annotations

import duckdb


def seed_demo_orders(conn: duckdb.DuckDBPyConnection) -> None:
    """Populate *conn* with the demo_orders star schema."""
    conn.execute("CREATE SCHEMA IF NOT EXISTS sales")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sales.customers (
            id              INTEGER,
            email           VARCHAR,
            region          VARCHAR,
            market_segment  VARCHAR
        )
    """)
    conn.execute("""
        INSERT INTO sales.customers VALUES
            (1, 'alice@example.com', 'NA',   'enterprise'),
            (2, 'bob@example.com',   'NA',   'smb'),
            (3, 'caro@example.com',  'EMEA', 'enterprise'),
            (4, 'dan@example.com',   'APAC', 'smb')
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sales.orders (
            order_id     INTEGER,
            order_number VARCHAR,
            customer_id  INTEGER,
            order_date   DATE,
            status       VARCHAR,
            amount       DOUBLE,
            discount     DOUBLE
        )
    """)
    conn.execute("""
        INSERT INTO sales.orders VALUES
            (10, 'ORD-010', 1, '2024-01-10', 'paid',    100.0,  5.0),
            (11, 'ORD-011', 1, '2024-01-15', 'paid',    200.0, 10.0),
            (12, 'ORD-012', 2, '2024-01-20', 'paid',     50.0,  0.0),
            (13, 'ORD-013', 2, '2024-02-01', 'pending',  75.0,  0.0),
            (14, 'ORD-014', 3, '2024-02-10', 'paid',    300.0, 15.0),
            (15, 'ORD-015', 4, '2024-02-15', 'pending', 125.0,  0.0)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sales.returns (
            return_id     INTEGER,
            customer_id   INTEGER,
            order_id      INTEGER,
            refund_amount DOUBLE
        )
    """)
    conn.execute("""
        INSERT INTO sales.returns VALUES
            (100, 1, 10, 20.0),
            (101, 3, 14, 50.0),
            (102, 4, 15, 10.0)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sales.line_items (
            order_id    INTEGER,
            line_number INTEGER,
            product_id  INTEGER,
            quantity    INTEGER,
            unit_price  DOUBLE
        )
    """)
    conn.execute("""
        INSERT INTO sales.line_items VALUES
            (10, 1, 101, 2, 50.0),
            (10, 2, 102, 1, 10.0),
            (11, 1, 103, 3, 66.67),
            (12, 1, 101, 1, 50.0),
            (13, 1, 104, 1, 75.0),
            (14, 1, 103, 2, 100.0),
            (14, 2, 105, 1, 100.0),
            (15, 1, 104, 1, 125.0)
    """)


def seed_tpcds(conn: duckdb.DuckDBPyConnection) -> None:
    """Populate *conn* with a deterministic miniature TPC-DS dataset."""
    conn.execute("CREATE SCHEMA IF NOT EXISTS tpcds")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tpcds.item (
            i_item_sk   INTEGER,
            i_category  VARCHAR,
            i_class     VARCHAR,
            i_brand     VARCHAR
        )
    """)
    conn.execute("""
        INSERT INTO tpcds.item VALUES
            (1, 'Books',  'fiction',   'acme'),
            (2, 'Books',  'nonfic',    'acme'),
            (3, 'Music',  'pop',       'zen'),
            (4, 'Music',  'classical', 'zen'),
            (5, 'Sports', 'running',   'fit')
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tpcds.customer (
            c_customer_sk         INTEGER,
            c_birth_country       VARCHAR,
            c_preferred_cust_flag VARCHAR
        )
    """)
    conn.execute("""
        INSERT INTO tpcds.customer VALUES
            (1, 'USA',    'Y'),
            (2, 'USA',    'N'),
            (3, 'CANADA', 'Y'),
            (4, 'MEXICO', 'N')
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tpcds.store (
            s_store_sk INTEGER,
            s_state    VARCHAR,
            s_country  VARCHAR
        )
    """)
    conn.execute("""
        INSERT INTO tpcds.store VALUES
            (10, 'CA', 'USA'),
            (11, 'NY', 'USA'),
            (12, 'ON', 'CANADA')
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tpcds.store_sales (
            ss_ticket_number   INTEGER,
            ss_item_sk         INTEGER,
            ss_customer_sk     INTEGER,
            ss_store_sk        INTEGER,
            ss_sold_date_sk    INTEGER,
            ss_quantity        INTEGER,
            ss_ext_sales_price DOUBLE,
            ss_net_profit      DOUBLE
        )
    """)
    conn.execute("""
        INSERT INTO tpcds.store_sales VALUES
            (1001, 1, 1, 10, 20250101, 2,  20.0,  8.0),
            (1001, 3, 1, 10, 20250101, 1,  15.0,  5.0),
            (1002, 2, 2, 11, 20250102, 3,  30.0, 10.0),
            (1002, 5, 2, 11, 20250102, 1,  50.0, 20.0),
            (1003, 4, 3, 12, 20250103, 2,  40.0, 15.0),
            (1004, 1, 3, 12, 20250104, 1,  10.0,  4.0),
            (1005, 5, 4, 10, 20250105, 2, 100.0, 40.0)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tpcds.store_returns (
            sr_ticket_number INTEGER,
            sr_item_sk       INTEGER,
            sr_customer_sk   INTEGER,
            sr_store_sk      INTEGER,
            sr_return_amt    DOUBLE
        )
    """)
    conn.execute("""
        INSERT INTO tpcds.store_returns VALUES
            (1002, 5, 2, 11, 50.0),
            (1005, 5, 4, 10, 25.0)
    """)


def seed_all(conn: duckdb.DuckDBPyConnection) -> None:
    """Seed both demo_orders and tpcds schemas into *conn*."""
    seed_demo_orders(conn)
    seed_tpcds(conn)
