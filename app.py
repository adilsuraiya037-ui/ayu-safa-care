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
except ImportError:
    psycopg2 = None


app = Flask(__name__)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

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


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db():

    # Render PostgreSQL
    if DATABASE_URL and psycopg2:

        url = DATABASE_URL

        if url.startswith("postgres://"):
            url = url.replace(
                "postgres://",
                "postgresql://",
                1
            )

        return psycopg2.connect(url)

    # Local SQLite
    conn = sqlite3.connect("orders.db")
    conn.row_factory = sqlite3.Row

    return conn


# --------------------------------------------------
# INITIALIZE DATABASE
# --------------------------------------------------

def init_db():

    conn = get_db()
    cursor = conn.cursor()

    # PostgreSQL
    if DATABASE_URL and psycopg2:

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                order_id VARCHAR(60) UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                product TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                amount REAL NOT NULL,
                status VARCHAR(20) DEFAULT 'NEW',
                created_at TEXT NOT NULL
            )
        """)

    # SQLite
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
    conn.close()


# --------------------------------------------------
# ADMIN LOGIN PROTECTION
# --------------------------------------------------

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get("admin_logged_in"):
            return redirect(
                url_for("admin_login")
            )

        return function(*args, **kwargs)

    return wrapper


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# --------------------------------------------------
# PLACE ORDER
# --------------------------------------------------

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

    except ValueError:

        return (
            "Invalid order information",
            400
        )

    # Required fields
    if not customer_name or not phone or not address or not product:

        return (
            "Please fill all required fields",
            400
        )

    if quantity < 1 or amount < 0:

        return (
            "Invalid quantity or amount",
            400
        )

    # Create unique order ID
    now = datetime.now()

    order_id = (
        "ASC"
        + now.strftime(
            "%Y%m%d%H%M%S"
        )
        + str(now.microsecond)[:3]
    )

    created_at = now.strftime(
        "%d-%m-%Y %I:%M %p"
    )

    conn = get_db()
    cursor = conn.cursor()

    # PostgreSQL
    if DATABASE_URL and psycopg2:

        cursor.execute("""
            INSERT INTO orders
            (
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

    # SQLite
    else:

        cursor.execute("""
            INSERT INTO orders
            (
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
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
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

    conn.commit()
    conn.close()

    # Order confirmation page
    return f"""
    <!DOCTYPE html>

    <html lang="en">

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>
            Order Confirmed - AYU SAFA CARE
        </title>

        <link
            rel="stylesheet"
            href="/static/style.css"
        >

    </head>

    <body>

        <section class="order-section">

            <div
                class="order-box"
                style="text-align:center;"
            >

                <div
                    style="
                        font-size:60px;
                        margin-bottom:20px;
                    "
                >
                    ✓
                </div>

                <h2
                    style="
                        color:#123d2d;
                        margin-bottom:15px;
                    "
                >
                    ORDER RECEIVED
                </h2>

                <p
                    style="
                        color:#68756f;
                        margin-bottom:10px;
                    "
                >
                    Thank you, {customer_name}.
                </p>

                <p
                    style="
                        color:#68756f;
                        margin-bottom:25px;
                    "
                >
                    Your order has been successfully placed.
                </p>

                <div class="total-box">

                    <span>
                        ORDER ID
                    </span>

                    <strong
                        style="font-size:18px;"
                    >
                        {order_id}
                    </strong>

                </div>

                <a
                    href="/"
                    class="primary-button"
                >
                    CONTINUE SHOPPING
                </a>

            </div>

        </section>

    </body>

    </html>
    """


# --------------------------------------------------
# TRACK ORDER
# --------------------------------------------------

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
                "Please enter Order ID and phone number."
            )

        else:

            conn = get_db()
            cursor = conn.cursor()

            # PostgreSQL
            if DATABASE_URL and psycopg2:

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

            # SQLite
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

            conn.close()

            if not order:

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


# --------------------------------------------------
# ADMIN LOGIN
# --------------------------------------------------

@app.route(
    "/admin",
    methods=["GET", "POST"]
)
def admin_login():

    if session.get("admin_logged_in"):

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


# --------------------------------------------------
# ADMIN DASHBOARD
# --------------------------------------------------

@app.route("/admin/dashboard")
@admin_required
def dashboard():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM orders
        ORDER BY id DESC
    """)

    orders = cursor.fetchall()

    # Total orders
    cursor.execute(
        "SELECT COUNT(*) FROM orders"
    )

    total_orders = cursor.fetchone()[0]

    # New
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'NEW'
        """
    )

    new_orders = cursor.fetchone()[0]

    # Confirmed
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'CONFIRMED'
        """
    )

    confirmed_orders = cursor.fetchone()[0]

    # Shipped
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'SHIPPED'
        """
    )

    shipped_orders = cursor.fetchone()[0]

    # Delivered
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'DELIVERED'
        """
    )

    delivered_orders = cursor.fetchone()[0]

    # Cancelled
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'CANCELLED'
        """
    )

    cancelled_orders = cursor.fetchone()[0]

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


# --------------------------------------------------
# UPDATE ORDER STATUS
# --------------------------------------------------

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

    conn = get_db()
    cursor = conn.cursor()

    # PostgreSQL
    if DATABASE_URL and psycopg2:

        cursor.execute("""
            UPDATE orders
            SET status = %s
            WHERE id = %s
        """, (
            status,
            order_id
        ))

    # SQLite
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
    conn.close()

    return redirect(
        url_for("dashboard")
    )


# --------------------------------------------------
# ADMIN LOGOUT
# --------------------------------------------------

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(
        url_for("admin_login")
    )


# --------------------------------------------------
# STARTUP
# --------------------------------------------------

init_db()


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
