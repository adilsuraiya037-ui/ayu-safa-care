from flask import (
    Flask,
    render_template,
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

        if url.startswith("postgresql://"):
            pass

        conn = psycopg2.connect(
            url,
            cursor_factory=RealDictCursor,
            connect_timeout=10
        )

        return conn

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
                    order_id VARCHAR(60) UNIQUE NOT NULL,
                    customer_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    address TEXT NOT NULL,
                    product TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    amount NUMERIC(10,2) NOT NULL,
                    status VARCHAR(20) DEFAULT 'NEW',
                    created_at TEXT NOT NULL
                )
            """)

        else:

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE NOT NULL,
                    customer_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    address TEXT NOT NULL,
                    product TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'NEW',
                    created_at TEXT NOT NULL
                )
            """)

        conn.commit()

        print("DATABASE INITIALIZATION: SUCCESS")
        print(
            "DATABASE TYPE:",
            "POSTGRESQL"
            if using_postgresql()
            else "SQLITE"
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("======================================")
        print("DATABASE INITIALIZATION ERROR")
        print(str(e))
        print("======================================")

        raise

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ==================================================
# ADMIN LOGIN PROTECTION
# ==================================================

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get(
            "admin_logged_in"
        ):

            return redirect(
                url_for("admin_login")
            )

        return function(
            *args,
            **kwargs
        )

    return wrapper


# ==================================================
# HOME PAGE
# ==================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ==================================================
# PLACE ORDER
# ==================================================

@app.route(
    "/place-order",
    methods=["POST"]
)
def place_order():

    # ----------------------------------------------
    # RECEIVE CUSTOMER INFORMATION
    # ----------------------------------------------

    customer_name = request.form.get(
        "customer_name",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    address = request.form.get(
        "address",
        ""
    ).strip()

    product = request.form.get(
        "product",
        ""
    ).strip()

    # ----------------------------------------------
    # BASIC VALIDATION
    # ----------------------------------------------

    if not customer_name:

        return (
            "Please enter your name.",
            400
        )

    if not phone:

        return (
            "Please enter your phone number.",
            400
        )

    if not address:

        return (
            "Please enter your delivery address.",
            400
        )

    if not product:

        return (
            "Please select a product.",
            400
        )

    # ----------------------------------------------
    # CHECK PRODUCT
    # ----------------------------------------------

    if product not in PRODUCT_PRICES:

        return (
            "Invalid product selected.",
            400
        )

    # ----------------------------------------------
    # QUANTITY
    # ----------------------------------------------

    try:

        quantity = int(
            request.form.get(
                "quantity",
                "1"
            )
        )

    except (ValueError, TypeError):

        return (
            "Invalid quantity.",
            400
        )

    if quantity < 1:

        return (
            "Invalid quantity.",
            400
        )

    if quantity > 100:

        return (
            "Maximum quantity allowed is 100.",
            400
        )

    # ----------------------------------------------
    # CALCULATE TOTAL ON SERVER
    # ----------------------------------------------

    unit_price = PRODUCT_PRICES[product]

    total_amount = (
        unit_price * quantity
    )

    # ----------------------------------------------
    # CREATE ORDER ID
    # ----------------------------------------------

    now = datetime.now()

    order_id = (
        "ASC"
        + now.strftime(
            "%Y%m%d%H%M%S"
        )
        + str(
            now.microsecond
        )[:3]
    )

    created_at = now.strftime(
        "%d-%m-%Y %I:%M %p"
    )

    # ----------------------------------------------
    # SAVE ORDER
    # ----------------------------------------------

    conn = None
    cursor = None

    try:

        print("======================================")
        print("NEW ORDER RECEIVED")
        print("Customer:", customer_name)
        print("Phone:", phone)
        print("Product:", product)
        print("Quantity:", quantity)
        print("Amount:", total_amount)
        print("Order ID:", order_id)
        print(
            "Database:",
            "POSTGRESQL"
            if using_postgresql()
            else "SQLITE"
        )
        print("======================================")

        conn = get_db()
        cursor = conn.cursor()

        # ------------------------------------------
        # POSTGRESQL
        # ------------------------------------------

        if using_postgresql():

            cursor.execute("""
                INSERT INTO orders (
                    order_id,
                    customer_name,
                    phone,
                    address,
                    product,
                    quantity,
                    amount,
                    status,
                    created_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING id
            """, (
                order_id,
                customer_name,
                phone,
                address,
                product,
                quantity,
                total_amount,
                "NEW",
                created_at
            ))

            inserted_row = cursor.fetchone()

        # ------------------------------------------
        # SQLITE
        # ------------------------------------------

        else:

            cursor.execute("""
                INSERT INTO orders (
                    order_id,
                    customer_name,
                    phone,
                    address,
                    product,
                    quantity,
                    amount,
                    status,
                    created_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                order_id,
                customer_name,
                phone,
                address,
                product,
                quantity,
                float(total_amount),
                "NEW",
                created_at
            ))

            inserted_row = {
                "id": cursor.lastrowid
            }

        conn.commit()

        print("ORDER SAVED SUCCESSFULLY")
        print(
            "DATABASE ORDER ID:",
            inserted_row["id"]
        )

    except Exception as e:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        print("======================================")
        print("ORDER DATABASE ERROR")
        print(str(e))
        print("======================================")

        return render_template(
            "order_success.html",
            error=True,
            error_message=(
                "We could not save your order. "
                "Please try again."
            )
        ), 500

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if conn:

            try:
                conn.close()
            except Exception:
                pass

    # ----------------------------------------------
    # SUCCESS
    # ----------------------------------------------

    return render_template(
        "order_success.html",
        customer_name=customer_name,
        order_id=order_id,
        product=product,
        quantity=quantity,
        amount=float(total_amount)
    )


# ==================================================
# TRACK ORDER
# ==================================================

@app.route(
    "/track-order",
    methods=["GET", "POST"]
)
def track_order():

    order = None
    error = None

    if request.method == "POST":

        order_id = request.form.get(
            "order_id",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        if not order_id or not phone:

            error = (
                "Please enter Order ID "
                "and phone number."
            )

        else:

            conn = None
            cursor = None

            try:

                conn = get_db()
                cursor = conn.cursor()

                if using_postgresql():

                    cursor.execute("""
                        SELECT
                            order_id,
                            customer_name,
                            phone,
                            product,
                            quantity,
                            amount,
                            status,
                            created_at
                        FROM orders
                        WHERE order_id = %s
                        AND phone = %s
                    """, (
                        order_id,
                        phone
                    ))

                else:

                    cursor.execute("""
                        SELECT
                            order_id,
                            customer_name,
                            phone,
                            product,
                            quantity,
                            amount,
                            status,
                            created_at
                        FROM orders
                        WHERE order_id = ?
                        AND phone = ?
                    """, (
                        order_id,
                        phone
                    ))

                order = cursor.fetchone()

            except Exception as e:

                print(
                    "TRACK ORDER ERROR:",
                    str(e)
                )

                error = (
                    "Unable to check order "
                    "right now."
                )

            finally:

                if cursor:

                    try:
                        cursor.close()
                    except Exception:
                        pass

                if conn:

                    try:
                        conn.close()
                    except Exception:
                        pass

            if not order and not error:

                error = (
                    "Order not found. "
                    "Please check your Order ID "
                    "and phone number."
                )

    return render_template(
        "track_order.html",
        order=order,
        error=error
    )


# ==================================================
# ADMIN LOGIN
# ==================================================

@app.route(
    "/admin",
    methods=["GET", "POST"]
)
def admin_login():

    if session.get(
        "admin_logged_in"
    ):

        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session[
                "admin_logged_in"
            ] = True

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid username or password."
        )

    return render_template(
        "admin_login.html"
    )


# ==================================================
# ADMIN DASHBOARD
# ==================================================

@app.route(
    "/admin/dashboard"
)
@admin_required
def dashboard():

    conn = None
    cursor = None

    try:

        conn = get_db()
        cursor = conn.cursor()

        # ------------------------------------------
        # ALL ORDERS
        # ------------------------------------------

        cursor.execute("""
            SELECT
                id,
                order_id,
                customer_name,
                phone,
                address,
                product,
                quantity,
                amount,
                status,
                created_at
            FROM orders
            ORDER BY id DESC
        """)

        orders = cursor.fetchall()

        # ------------------------------------------
        # TOTAL
        # ------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM orders
        """)

        total_orders = cursor.fetchone()["count"]

        # ------------------------------------------
        # NEW
        # ------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM orders
            WHERE status = 'NEW'
        """)

        new_orders = cursor.fetchone()["count"]

        # ------------------------------------------
        # CONFIRMED
        # ------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM orders
            WHERE status = 'CONFIRMED'
        """)

        confirmed_orders = cursor.fetchone()["count"]

        # ------------------------------------------
        # SHIPPED
        # ------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM orders
            WHERE status = 'SHIPPED'
        """)

        shipped_orders = cursor.fetchone()["count"]

        # ------------------------------------------
        # DELIVERED
        # ------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM orders
            WHERE status = 'DELIVERED'
        """)

        delivered_orders = cursor.fetchone()["count"]

        # ------------------------------------------
        # CANCELLED
        # ------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM orders
            WHERE status = 'CANCELLED'
        """)

        cancelled_orders = cursor.fetchone()["count"]

    except Exception as e:

        print("======================================")
        print("DASHBOARD DATABASE ERROR")
        print(str(e))
        print("======================================")

        return (
            "Unable to load orders. "
            "Please check the database connection.",
            500
        )

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if conn:

            try:
                conn.close()
            except Exception:
                pass

    return render_template(
        "dashboard.html",
        orders=orders,
        total_orders=total_orders,
        new_orders=new_orders,
        confirmed_orders=confirmed_orders,
        shipped_orders=shipped_orders,
        delivered_orders=delivered_orders,
        cancelled_orders=cancelled_orders
    )


# ==================================================
# UPDATE ORDER STATUS
# ==================================================

@app.route(
    "/admin/update-status/<int:order_id>",
    methods=["POST"]
)
@admin_required
def update_status(order_id):

    status = request.form.get(
        "status",
        "NEW"
    ).strip().upper()

    allowed = [
        "NEW",
        "CONFIRMED",
        "SHIPPED",
        "DELIVERED",
        "CANCELLED"
    ]

    if status not in allowed:

        return (
            "Invalid status",
            400
        )

    conn = None
    cursor = None

    try:

        conn = get_db()
        cursor = conn.cursor()

        if using_postgresql():

            cursor.execute("""
                UPDATE orders
                SET status = %s
                WHERE id = %s
            """, (
                status,
                order_id
            ))

        else:

            cursor.execute("""
                UPDATE orders
                SET status = ?
                WHERE id = ?
            """, (
                status,
                order_id
            ))

        conn.commit()

    except Exception as e:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        print(
            "STATUS UPDATE ERROR:",
            str(e)
        )

        return (
            "Unable to update order status.",
            500
        )

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if conn:

            try:
                conn.close()
            except Exception:
                pass

    return redirect(
        url_for("dashboard")
    )


# ==================================================
# ADMIN LOGOUT
# ==================================================

@app.route(
    "/admin/logout"
)
def admin_logout():

    session.clear()

    return redirect(
        url_for("admin_login")
    )


# ==================================================
# DATABASE STARTUP
# ==================================================

init_db()


# ==================================================
# FLASK START
# ==================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
