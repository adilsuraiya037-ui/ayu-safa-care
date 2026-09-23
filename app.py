import os
from flask import Flask, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static"
)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/order", methods=["POST"])
def order():
    name = request.form.get("name", "")
    phone = request.form.get("phone", "")
    address = request.form.get("address", "")
    product = request.form.get("product", "")
    quantity = request.form.get("quantity", "1")

    prices = {
        "Hair Oil": 299,
        "Herbal Shampoo": 149,
        "Malam": 199
    }

    price = prices.get(product, 0)
    total = price * int(quantity)

    return render_template(
        "thankyou.html",
        name=name,
        phone=phone,
        address=address,
        product=product,
        quantity=quantity,
        total=total
    )


if __name__ == "__main__":
    app.run(debug=True)