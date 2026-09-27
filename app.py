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
    "admin"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "admin123"
)

DATABASE_URL = os.environ.get("DATABASE_URL")


# ==================================================
# DATABASE CONNECTION
# ==================================================

def using_postgresql():
    return bool(DATABASE_URL and psycopg2)


def get_db():

    # ----------------------------------------------
    # RENDER POSTGRESQL
    # ----------------------------------------------

    if using_postgresql():

        url = DATABASE_URL

        if url.startswith("postgres://"):
            url = url.replace(
                "postgres://",
                "postgresql://",
                1
            )

        conn = psycopg2.connect(
            url,
            cursor_factory=RealDictCursor
        )

        return conn

    # ----------------------------------------------
    # LOCAL SQLITE
    # ----------------------------------------------

    conn = sqlite3.connect(
        "orders.db"
    )

    conn.row_factory = sqlite3.Row

    return conn


# ==================================================
# INITIALIZE DATABASE
# ==================================================

def init_db():

    conn = get_db()
    cursor = conn.cursor()

    try:

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

    except Exception:

        conn.rollback()
        raise

    finally:

        cursor.close()
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
# HOME
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

    try:

        quantity = int(
            request.form.get(
                "quantity",
                "1"
            )
        )

        amount = float(
            request.form.get(
                "amount",
                "0"
            )
        )

    except (ValueError, TypeError):

        return (
            "Invalid order information",
            400
        )

    # ----------------------------------------------
    # VALIDATION
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

    if quantity < 1:

        return (
            "Invalid quantity.",
            400
        )

    if amount < 0:

        return (
            "Invalid amount.",
            400
        )

    # ----------------------------------------------
    # ORDER ID
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

        conn = get_db()
        cursor = conn.cursor()

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
            """, (
                order_id,
                customer_name,
                phone,
                address,
                product,
                quantity,
                amount,
                "NEW",
                created_at
            ))

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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                customer_name,
                phone,
                address,
                product,
                quantity,
                amount,
                "NEW",
                created_at
            ))

        conn.commit()

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "ORDER DATABASE ERROR:",
            str(e)
        )

        return (
            "Unable to save your order. "
            "Please try again.",
            500
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    # ----------------------------------------------
    # CONFIRMATION
    # ----------------------------------------------

    return render_template(
        "order_success.html",
        customer_name=customer_name,
        order_id=order_id,
        product=product,
        quantity=quantity,
        amount=amount
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
                    cursor.close()

                if conn:
                    conn.close()

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
        )

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
        # COUNTS
        # ------------------------------------------

        cursor.execute(
            "SELECT COUNT(*) AS count FROM orders"
        )

        total_orders = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM orders
            WHERE status = 'NEW'
        """)

        new_orders = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM orders
            WHERE status = 'CONFIRMED'
        """)

        confirmed_orders = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM orders
            WHERE status = 'SHIPPED'
        """)

        shipped_orders = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM orders
            WHERE status = 'DELIVERED'
        """)

        delivered_orders = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM orders
            WHERE status = 'CANCELLED'
        """)

        cancelled_orders = cursor.fetchone()["count"]

    except Exception as e:

        print(
            "DASHBOARD DATABASE ERROR:",
            str(e)
        )

        return (
            "Unable to load orders. "
            "Please check the database connection.",
            500
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

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
    )

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
            conn.rollback()

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
            cursor.close()

        if conn:
            conn.close()

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
# START DATABASE
# ==================================================

init_db()


# ==================================================
# START FLASK
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
