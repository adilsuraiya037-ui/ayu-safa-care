from flask import (
    Flask,
    render_template,
    render_template_string,
    request,
    redirect,
    url_for,
    session,
    flash
)
from functools import wraps
from datetime import datetime
from decimal import Decimal
import os
import sqlite3
import uuid

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None


app = Flask(__name__)


# ==================================================
# CONFIGURATION
# ==================================================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "local-secret-key"
)

ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "dr.adil"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "ayusafa786"
)

DATABASE_URL = os.environ.get("DATABASE_URL")


# ==================================================
# PRODUCT PRICES
# ==================================================

PRODUCT_PRICES = {
    "Gold Herbal Hair Oil": Decimal("299.00"),
    "Herbal Hair Shampoo": Decimal("149.00"),
    "Ayu Safa Care Malam": Decimal("149.00")
}


# ==================================================
# DATABASE TYPE
# ==================================================

def using_postgresql():

    return bool(
        DATABASE_URL and psycopg2
    )


# ==================================================
# DATABASE CONNECTION
# ==================================================

def get_db():

    # ----------------------------------------------
    # POSTGRESQL
    # ----------------------------------------------

    if using_postgresql():

        url = DATABASE_URL.strip()

        if url.startswith("postgres://"):

            url = url.replace(
                "postgres://",
                "postgresql://",
                1
            )

        return psycopg2.connect(
            url,
            cursor_factory=RealDictCursor,
            connect_timeout=10
        )

    # ----------------------------------------------
    # SQLITE
    # ----------------------------------------------

    conn = sqlite3.connect(
        "orders.db",
        timeout=10
    )

    conn.row_factory = sqlite3.Row

    return conn


# ==================================================
# INITIALIZE DATABASE
# ==================================================

def init_db():

    conn = None
    cursor = None

    try:

        conn = get_db()
        cursor = conn.cursor()

        if using_postgresql():

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (

                    id SERIAL PRIMARY KEY,

                    order_id VARCHAR(60)
                    UNIQUE NOT NULL,

                    customer_name TEXT
                    NOT NULL,

                    phone TEXT
                    NOT NULL,

                    address TEXT
                    NOT NULL,

                    product TEXT
                    NOT NULL,

                    quantity INTEGER
                    NOT NULL,

                    amount NUMERIC(10,2)
                    NOT NULL,

                    status VARCHAR(20)
                    DEFAULT 'NEW',

                    created_at TEXT
                    NOT NULL
                )
            """)

        else:

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (

                    id INTEGER
                    PRIMARY KEY AUTOINCREMENT,

                    order_id TEXT
                    UNIQUE NOT NULL,

                    customer_name TEXT
                    NOT NULL,

                    phone TEXT
                    NOT NULL,

                    address TEXT
                    NOT NULL,

                    product TEXT
                    NOT NULL,

                    quantity INTEGER
                    NOT NULL,

                    amount REAL
                    NOT NULL,
