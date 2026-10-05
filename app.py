from flask import (
    Flask,
    render_template,
    render_template_string,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
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

from jinja2 import TemplateNotFound


app = Flask(__name__)


# =========================================================
# CONFIGURATION
# =========================================================

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


# =========================================================
# DEFAULT PRODUCTS
# =========================================================
#
# These are used only to create the initial product list.
#
# After the products table is created, products can be
# managed from the Admin page.
#
# =========================================================

DEFAULT_PRODUCTS = [
    {
        "name": "Gold Herbal Hair Oil",
        "price": Decimal("299.00"),
        "image": "hair-oil.jpg"
    },
    {
        "name": "Herbal Hair Shampoo",
        "price": Decimal("149.00"),
        "image": "shampoo.jpg"
    },
    {
        "name": "Ayu Safa Care Malam",
        "price": Decimal("149.00"),
        "image": "Malam.jpg"
    }
]


# =========================================================
# DATABASE TYPE
# =========================================================

def using_postgresql():

    return bool(
        DATABASE_URL and psycopg2
    )


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():

    # -----------------------------------------------------
    # POSTGRESQL
    # -----------------------------------------------------

    if using_postgresql():

        url = DATABASE_URL.strip()

        if url.startswith("postgres://"):

            url = url.replace(
                "postgres://",
                "postgresql://",
                1
            )

        conn = psycopg2.connect(
            url,
            cursor_factory=RealDictCursor,
            connect_timeout=10
        )

        return conn

    # -----------------------------------------------------
    # SQLITE
    # -----------------------------------------------------

    conn = sqlite3.connect(
        "orders.db",
        timeout=10
    )

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# INITIALIZE DATABASE
# =========================================================

def init_db():

    conn = None
    cursor = None

    try:

        conn = get_db()
        cursor = conn.cursor()

        # =================================================
        # ORDERS TABLE
        # =================================================

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

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

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

                    status TEXT
                        DEFAULT 'NEW',

                    created_at TEXT
                        NOT NULL
                )
            """)

        # =================================================
        # ORDER ITEMS TABLE
        # =================================================

        if using_postgresql():

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_items (

                    id SERIAL PRIMARY KEY,

                    order_id VARCHAR(60)
                        NOT NULL,

                    product TEXT
                        NOT NULL,

                    quantity INTEGER
                        NOT NULL,

                    unit_price NUMERIC(10,2)
                        NOT NULL,

                    total_price NUMERIC(10,2)
                        NOT NULL
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_order_items_order_id
                ON order_items(order_id)
            """)

        else:

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_items (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    order_id TEXT
                        NOT NULL,

                    product TEXT
                        NOT NULL,

                    quantity INTEGER
                        NOT NULL,

                    unit_price REAL
                        NOT NULL,

                    total_price REAL
                        NOT NULL
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_order_items_order_id
                ON order_items(order_id)
            """)

        # =================================================
        # PRODUCTS TABLE
        # =================================================
        #
        # This is the new important part.
        #
        # Admin can add products.
        #
        # Product automatically becomes available to the
        # website once added.
        #
        # =================================================

        if using_postgresql():

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (

                    id SERIAL PRIMARY KEY,

                    name TEXT
                        UNIQUE NOT NULL,

                    price NUMERIC(10,2)
                        NOT NULL,

                    image TEXT,

                    active BOOLEAN
                        DEFAULT TRUE,

                    created_at TEXT
                        NOT NULL
                )
            """)

        else:

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    name TEXT
                        UNIQUE NOT NULL,

                    price REAL
                        NOT NULL,

                    image TEXT,

                    active INTEGER
                        DEFAULT 1,

                    created_at TEXT
                        NOT NULL
                )
            """)

        # =================================================
        # INSERT DEFAULT PRODUCTS IF TABLE IS EMPTY
        # =================================================

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM products
        """)

        product_count = cursor.fetchone()["count"]

        if product_count == 0:

            created_at = datetime.now().strftime(
                "%d-%m-%Y %I:%M %p"
            )

            for product in DEFAULT_PRODUCTS:

                if using_postgresql():

                    cursor.execute("""
                        INSERT INTO products (
                            name,
                            price,
                            image,
                            active,
                            created_at
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                        ON CONFLICT (name)
                        DO NOTHING
                    """, (
                        product["name"],
                        product["price"],
                        product["image"],
                        True,
                        created_at
                    ))

                else:

                    cursor.execute("""
                        INSERT OR IGNORE INTO products (
                            name,
                            price,
                            image,
                            active,
                            created_at
                        )
                        VALUES (
                            ?, ?, ?, ?, ?
                        )
                    """, (
                        product["name"],
                        float(product["price"]),
                        product["image"],
                        1,
                        created_at
                    ))

        conn.commit()

        print("======================================")
        print("DATABASE INITIALIZATION: SUCCESS")
        print(
            "DATABASE TYPE:",
            "POSTGRESQL"
            if using_postgresql()
            else "SQLITE"
        )
        print("MULTI PRODUCT SYSTEM: ENABLED")
        print("PRODUCT MANAGEMENT: ENABLED")
        print("======================================")

    except Exception as e:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        print("======================================")
        print("DATABASE INITIALIZATION ERROR")
        print(str(e))
        print("======================================")

        raise

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


# =========================================================
# GET PRODUCTS
# =========================================================

def get_products():

    conn = None
    cursor = None

    try:

        conn = get_db()
        cursor = conn.cursor()

        if using_postgresql():

            cursor.execute("""
                SELECT
                    id,
                    name,
                    price,
                    image,
                    active,
                    created_at
                FROM products
                WHERE active = TRUE
                ORDER BY id ASC
            """)

        else:

            cursor.execute("""
                SELECT
                    id,
                    name,
                    price,
                    image,
                    active,
                    created_at
                FROM products
                WHERE active = 1
                ORDER BY id ASC
            """)

        products = cursor.fetchall()

        return products

    except Exception as e:

        print(
            "GET PRODUCTS ERROR:",
            str(e)
        )

        return []

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


# =========================================================
# PRODUCT PRICE LOOKUP
# =========================================================

def get_product_prices():

    products = get_products()

    prices = {}

    for product in products:

        prices[
            product["name"]
        ] = Decimal(
            str(product["price"])
        )

    return prices


# =========================================================
# SAFE ORDER SUCCESS PAGE
# =========================================================

def show_order_success(
    customer_name=None,
    order_id=None,
    product=None,
    quantity=None,
    amount=None,
    items=None,
    error=False,
    error_message=None
):

    try:

        return render_template(
            "order_success.html",

            customer_name=customer_name,

            order_id=order_id,

            product=product,

            quantity=quantity,

            amount=amount,

            items=items,

            error=error,

            error_message=error_message
        )

    except TemplateNotFound:

        print(
            "WARNING: order_success.html was not found."
        )

        # =================================================
        # SUCCESS FALLBACK
        # =================================================

        if not error:

            return render_template_string("""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Order Successful - Ayu Safa Care</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    padding: 0;
    font-family: Arial, sans-serif;
    background: #f4f7f4;
    color: #222;
}

.container {
    max-width: 650px;
    margin: 50px auto;
    padding: 20px;
}

.card {
    background: white;
    border-radius: 20px;
    padding: 35px 25px;
    text-align: center;
    box-shadow:
        0 8px 30px rgba(0,0,0,0.10);
}

.success-icon {
    width: 70px;
    height: 70px;
    margin: 0 auto 20px;
    border-radius: 50%;
    background: #198754;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 38px;
    font-weight: bold;
}

h1 {
    color: #176b3a;
}

.message {
    color: #555;
}

.order-box {
    text-align: left;
    background: #f5f7f5;
    border-radius: 12px;
    padding: 20px;
    margin-top: 20px;
}

.row {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    padding: 10px 0;
    border-bottom: 1px solid #ddd;
}

.row:last-child {
    border-bottom: none;
}

.label {
    font-weight: bold;
}

.value {
    text-align: right;
}

.order-id {
    color: #176b3a;
    font-weight: bold;
    word-break: break-all;
}

.items {
    margin-top: 15px;
}

.item {
    display: flex;
    justify-content: space-between;
    gap: 15px;
    padding: 9px 0;
}

.btn {
    display: inline-block;
    margin: 20px 5px 0;
    padding: 13px 22px;
    border-radius: 8px;
    text-decoration: none;
    font-weight: bold;
}

.home {
    background: #176b3a;
    color: white;
}

.track {
    background: #222;
    color: white;
}

</style>

</head>

<body>

<div class="container">

<div class="card">

<div class="success-icon">
✓
</div>

<h1>
Order Placed Successfully!
</h1>

<p class="message">
Thank you, {{ customer_name }}.
Your order has been received successfully.
</p>

<div class="order-box">

<div class="row">

<span class="label">
Order ID
</span>

<span class="value order-id">
{{ order_id }}
</span>

</div>

{% if items %}

<div class="items">

{% for item in items %}

<div class="item">

<span>
{{ item.product }}
× {{ item.quantity }}
</span>

<strong>
₹{{ "%.2f"|format(item.total_price) }}
</strong>

</div>

{% endfor %}

</div>

{% endif %}

<div class="row">

<span class="label">
Total Amount
</span>

<span class="value">
₹{{ "%.2f"|format(amount) }}
</span>

</div>

</div>

<a
href="{{ url_for('index') }}"
class="btn home"
>
Continue Shopping
</a>

<a
href="{{ url_for('track_order') }}"
class="btn track"
>
Track Order
</a>

</div>

</div>

</body>

</html>
            """,
                customer_name=customer_name,
                order_id=order_id,
                product=product,
                quantity=quantity,
                amount=amount,
                items=items
            )

        # =================================================
        # ERROR FALLBACK
        # =================================================

        return render_template_string("""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Order Error</title>

<style>

body {
    margin: 0;
    padding: 30px;
    font-family: Arial, sans-serif;
    background: #f5f5f5;
}

.box {
    max-width: 550px;
    margin: 50px auto;
    background: white;
    padding: 35px;
    border-radius: 15px;
    text-align: center;
    box-shadow:
        0 5px 25px rgba(0,0,0,0.10);
}

h1 {
    color: #b02a37;
}

a {
    display: inline-block;
    margin-top: 20px;
    padding: 12px 22px;
    background: #176b3a;
    color: white;
    text-decoration: none;
    border-radius: 8px;
}

</style>

</head>

<body>

<div class="box">

<h1>
Order Could Not Be Saved
</h1>

<p>
{{ error_message }}
</p>

<a href="{{ url_for('index') }}">
Return to Website
</a>

</div>

</body>

</html>
        """,
            error_message=error_message
        )


# =========================================================
# ADMIN LOGIN PROTECTION
# =========================================================

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


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def index():

    products = get_products()

    return render_template(
        "index.html",
        products=products
    )


# =========================================================
# READ MULTIPLE PRODUCTS
# =========================================================

def get_order_items_from_form():

    items = []

    product_prices = get_product_prices()

    # =====================================================
    # MULTIPLE PRODUCT FORMAT
    # =====================================================

    for i in range(1, 51):

        product = request.form.get(
            f"product_{i}",
            ""
        ).strip()

        quantity_raw = request.form.get(
            f"quantity_{i}",
            ""
        ).strip()

        if not product:

            continue

        if product not in product_prices:

            raise ValueError(
                f"Invalid product selected: {product}"
            )

        if not quantity_raw:

            quantity = 1

        else:

            try:

                quantity = int(
                    quantity_raw
                )

            except (
                ValueError,
                TypeError
            ):

                raise ValueError(
                    "Invalid quantity."
                )

        if quantity < 1:

            raise ValueError(
                "Quantity must be at least 1."
            )

        if quantity > 100:

            raise ValueError(
                "Maximum quantity per product is 100."
            )

        unit_price = product_prices[
            product
        ]

        total_price = (
            unit_price * quantity
        )

        items.append({

            "product": product,

            "quantity": quantity,

            "unit_price": unit_price,

            "total_price": total_price

        })

    # =====================================================
    # OLD SINGLE PRODUCT FORMAT
    # =====================================================

    if not items:

        old_product = request.form.get(
            "product",
            ""
        ).strip()

        if old_product:

            if old_product not in product_prices:

                raise ValueError(
                    "Invalid product selected."
                )

            try:

                old_quantity = int(
                    request.form.get(
                        "quantity",
                        "1"
                    )
                )

            except (
                ValueError,
                TypeError
            ):

                raise ValueError(
                    "Invalid quantity."
                )

            if old_quantity < 1:

                raise ValueError(
                    "Invalid quantity."
                )

            if old_quantity > 100:

                raise ValueError(
                    "Maximum quantity allowed is 100."
                )

            unit_price = product_prices[
                old_product
            ]

            total_price = (
                unit_price * old_quantity
            )

            items.append({

                "product": old_product,

                "quantity": old_quantity,

                "unit_price": unit_price,

                "total_price": total_price

            })

    return items


# =========================================================
# PLACE ORDER
# =========================================================

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

    try:

        items = get_order_items_from_form()

    except ValueError as e:

        return (
            str(e),
            400
        )

    if not items:

        return (
            "Please select at least one product.",
            400
        )

    # =====================================================
    # CALCULATE TOTAL
    # =====================================================

    total_amount = Decimal("0.00")

    total_quantity = 0

    for item in items:

        total_amount += item[
            "total_price"
        ]

        total_quantity += item[
            "quantity"
        ]

    # =====================================================
    # PRODUCT SUMMARY
    # =====================================================

    product_summary_parts = []

    for item in items:

        product_summary_parts.append(
            "{} × {}".format(
                item["product"],
                item["quantity"]
            )
        )

    product_summary = ", ".join(
        product_summary_parts
    )

    # =====================================================
    # ORDER ID
    # =====================================================

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

    conn = None
    cursor = None

    try:

        print("======================================")
        print("NEW ORDER RECEIVED")
        print("Customer:", customer_name)
        print("Phone:", phone)
        print("Products:", product_summary)
        print("Total Quantity:", total_quantity)
        print("Amount:", total_amount)
        print("Order ID:", order_id)
        print("======================================")

        conn = get_db()

        cursor = conn.cursor()

        # =================================================
        # MAIN ORDER
        # =================================================

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
                product_summary,
                total_quantity,
                total_amount,
                "NEW",
                created_at

            ))

            inserted_row = cursor.fetchone()

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
                product_summary,
                total_quantity,
                float(total_amount),
                "NEW",
                created_at

            ))

            inserted_row = {
                "id": cursor.lastrowid
            }

        # =================================================
        # ORDER ITEMS
        # =================================================

        for item in items:

            if using_postgresql():

                cursor.execute("""
                    INSERT INTO order_items (

                        order_id,
                        product,
                        quantity,
                        unit_price,
                        total_price

                    )

                    VALUES (

                        %s,
                        %s,
                        %s,
                        %s,
                        %s

                    )

                """, (

                    order_id,
                    item["product"],
                    item["quantity"],
                    item["unit_price"],
                    item["total_price"]

                ))

            else:

                cursor.execute("""
                    INSERT INTO order_items (

                        order_id,
                        product,
                        quantity,
                        unit_price,
                        total_price

                    )

                    VALUES (

                        ?, ?, ?, ?, ?

                    )

                """, (

                    order_id,
                    item["product"],
                    item["quantity"],
                    float(
                        item["unit_price"]
                    ),
                    float(
                        item["total_price"]
                    )

                ))

        conn.commit()

        print(
            "ORDER SAVED SUCCESSFULLY"
        )

        print(
            "DATABASE ORDER ID:",
            inserted_row["id"]
        )

        print(
            "ORDER ITEMS:",
            len(items)
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

        return show_order_success(
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

    return show_order_success(
        customer_name=customer_name,
        order_id=order_id,
        product=product_summary,
        quantity=total_quantity,
        amount=float(total_amount),
        items=items
    )


# =========================================================
# TRACK ORDER
# =========================================================

@app.route(
    "/track-order",
    methods=["GET", "POST"]
)
def track_order():

    order = None
    order_items = []
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

                # =================================================
                # FIND MAIN ORDER
                # =================================================

                if using_postgresql():

                    cursor.execute("""
                        SELECT

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

                        WHERE order_id = %s
                        AND phone = %s

                        LIMIT 1

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
                            address,
                            product,
                            quantity,
                            amount,
                            status,
                            created_at

                        FROM orders

                        WHERE order_id = ?
                        AND phone = ?

                        LIMIT 1

                    """, (
                        order_id,
                        phone
                    ))

                row = cursor.fetchone()

                if row:

                    order = {

                        "order_id":
                            row["order_id"],

                        "customer_name":
                            row["customer_name"],

                        "phone":
                            row["phone"],

                        "address":
                            row["address"],

                        "product":
                            row["product"],

                        "quantity":
                            row["quantity"],

                        "amount":
                            row["amount"],

                        "status":
                            row["status"],

                        "created_at":
                            row["created_at"]

                    }

                    # =================================================
                    # FIND ALL ITEMS
                    # =================================================

                    if using_postgresql():

                        cursor.execute("""
                            SELECT

                                product,
                                quantity,
                                unit_price,
                                total_price

                            FROM order_items

                            WHERE order_id = %s

                            ORDER BY id ASC

                        """, (
                            order_id,
                        ))

                    else:

                        cursor.execute("""
                            SELECT

                                product,
                                quantity,
                                unit_price,
                                total_price

                            FROM order_items

                            WHERE order_id = ?

                            ORDER BY id ASC

                        """, (
                            order_id,
                        ))

                    rows = cursor.fetchall()

                    for item in rows:

                        order_items.append({

                            "product":
                                item["product"],

                            "quantity":
                                item["quantity"],

                            "unit_price":
                                item["unit_price"],

                            "total_price":
                                item["total_price"]

                        })

            except Exception as e:

                print("======================================")
                print("TRACK ORDER ERROR")
                print(str(e))
                print("======================================")

                error = (
                    "Unable to check your order "
                    "right now. Please try again."
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
        order_items=order_items,
        error=error
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

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


# =========================================================
# ADMIN DASHBOARD
# =========================================================

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

        # =================================================
        # ORDERS
        # =================================================

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

        # =================================================
        # PRODUCT LIST
        # =================================================

        cursor.execute("""
            SELECT

                id,
                name,
                price,
                image,
                active,
                created_at

            FROM products

            ORDER BY id ASC
        """)

        products = cursor.fetchall()

        # =================================================
        # ORDER COUNTS
        # =================================================

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM orders
        """)

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

        print("======================================")
        print("DASHBOARD DATABASE ERROR")
        print(str(e))
        print("======================================")

        return (
            "Unable to load dashboard. "
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

        products=products,

        total_orders=total_orders,

        new_orders=new_orders,

        confirmed_orders=confirmed_orders,

        shipped_orders=shipped_orders,

        delivered_orders=delivered_orders,

        cancelled_orders=cancelled_orders
    )


# =========================================================
# ADD PRODUCT - ADMIN
# =========================================================

@app.route(
    "/admin/add-product",
    methods=["POST"]
)
@admin_required
def add_product():

    name = request.form.get(
        "name",
        ""
    ).strip()

    price_raw = request.form.get(
        "price",
        ""
    ).strip()

    image = request.form.get(
        "image",
        ""
    ).strip()

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not name:

        flash(
            "Please enter product name."
        )

        return redirect(
            url_for("dashboard")
        )

    if not price_raw:

        flash(
            "Please enter product price."
        )

        return redirect(
            url_for("dashboard")
        )

    try:

        price = Decimal(
            price_raw
        )

    except Exception:

        flash(
            "Invalid product price."
        )

        return redirect(
            url_for("dashboard")
        )

    if price <= 0:

        flash(
            "Product price must be greater than zero."
        )

        return redirect(
            url_for("dashboard")
        )

    if price > Decimal("999999.99"):

        flash(
            "Product price is too high."
        )

        return redirect(
            url_for("dashboard")
        )

    # Default image
    if not image:

        image = "product-placeholder.jpg"

    created_at = datetime.now().strftime(
        "%d-%m-%Y %I:%M %p"
    )

    conn = None
    cursor = None

    try:

        conn = get_db()
        cursor = conn.cursor()

        # =================================================
        # POSTGRESQL
        # =================================================

        if using_postgresql():

            cursor.execute("""
                INSERT INTO products (
                    name,
                    price,
                    image,
                    active,
                    created_at
                )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """, (
                name,
                price,
                image,
                True,
                created_at
            ))

        # =================================================
        # SQLITE
        # =================================================

        else:

            cursor.execute("""
                INSERT INTO products (
                    name,
                    price,
                    image,
                    active,
                    created_at
                )

                VALUES (
                    ?, ?, ?, ?, ?
                )
            """, (
                name,
                float(price),
                image,
                1,
                created_at
            ))

        conn.commit()

        flash(
            f"{name} added successfully."
        )

    except Exception as e:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        print(
            "ADD PRODUCT ERROR:",
            str(e)
        )

        # Duplicate product
        if "unique" in str(e).lower():

            flash(
                "This product already exists."
            )

        else:

            flash(
                "Unable to add product."
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


# =========================================================
# TOGGLE PRODUCT
# =========================================================
#
# This lets admin hide/show a product without deleting it.
#
# =========================================================

@app.route(
    "/admin/toggle-product/<int:product_id>",
    methods=["POST"]
)
@admin_required
def toggle_product(product_id):

    conn = None
    cursor = None

    try:

        conn = get_db()
        cursor = conn.cursor()

        # -------------------------------------------------
        # GET CURRENT STATE
        # -------------------------------------------------

        if using_postgresql():

            cursor.execute("""
                SELECT active
                FROM products
                WHERE id = %s
            """, (
                product_id,
            ))

        else:

            cursor.execute("""
                SELECT active
                FROM products
                WHERE id = ?
            """, (
                product_id,
            ))

        product = cursor.fetchone()

        if not product:

            flash(
                "Product not found."
            )

            return redirect(
                url_for("dashboard")
            )

        current_active = product["active"]

        # -------------------------------------------------
        # TOGGLE
        # -------------------------------------------------

        new_active = not bool(
            current_active
        )

        if using_postgresql():

            cursor.execute("""
                UPDATE products

                SET active = %s

                WHERE id = %s
            """, (
                new_active,
                product_id
            ))

        else:

            cursor.execute("""
                UPDATE products

                SET active = ?

                WHERE id = ?
            """, (
                1 if new_active else 0,
                product_id
            ))

        conn.commit()

        flash(
            "Product visibility updated."
        )

    except Exception as e:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        print(
            "TOGGLE PRODUCT ERROR:",
            str(e)
        )

        flash(
            "Unable to update product."
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


# =========================================================
# DELETE PRODUCT
# =========================================================

@app.route(
    "/admin/delete-product/<int:product_id>",
    methods=["POST"]
)
@admin_required
def delete_product(product_id):

    conn = None
    cursor = None

    try:

        conn = get_db()
        cursor = conn.cursor()

        if using_postgresql():

            cursor.execute("""
                DELETE FROM products
                WHERE id = %s
            """, (
                product_id,
            ))

        else:

            cursor.execute("""
                DELETE FROM products
                WHERE id = ?
            """, (
                product_id,
            ))

        conn.commit()

        flash(
            "Product deleted successfully."
        )

    except Exception as e:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        print(
            "DELETE PRODUCT ERROR:",
            str(e)
        )

        flash(
            "Unable to delete product."
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


# =========================================================
# GET ORDER ITEMS FOR ADMIN
# =========================================================

@app.route(
    "/admin/order-items/<order_id>"
)
@admin_required
def admin_order_items(order_id):

    conn = None
    cursor = None

    try:

        conn = get_db()
        cursor = conn.cursor()

        if using_postgresql():

            cursor.execute("""
                SELECT

                    product,
                    quantity,
                    unit_price,
                    total_price

                FROM order_items

                WHERE order_id = %s

                ORDER BY id ASC

            """, (
                order_id,
            ))

        else:

            cursor.execute("""
                SELECT

                    product,
                    quantity,
                    unit_price,
                    total_price

                FROM order_items

                WHERE order_id = ?

                ORDER BY id ASC

            """, (
                order_id,
            ))

        items = cursor.fetchall()

        result = []

        for item in items:

            result.append({

                "product":
                    item["product"],

                "quantity":
                    item["quantity"],

                "unit_price":
                    float(
                        item["unit_price"]
                    ),

                "total_price":
                    float(
                        item["total_price"]
                    )

            })

        return jsonify(result)

    except Exception as e:

        print(
            "ADMIN ORDER ITEMS ERROR:",
            str(e)
        )

        return jsonify({

            "error":
                "Unable to load order items."

        }), 500

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


# =========================================================
# UPDATE ORDER STATUS
# =========================================================

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


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route(
    "/admin/logout"
)
def admin_logout():

    session.clear()

    return redirect(
        url_for("admin_login")
    )


# =========================================================
# DATABASE STARTUP
# =========================================================

init_db()


# =========================================================
# FLASK START
# =========================================================

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
