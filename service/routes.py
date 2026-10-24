
######################################################################
# Copyright 2016, 2022 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

"""
Product Store Service with UI
"""

from decimal import Decimal, InvalidOperation

from flask import jsonify, request, abort, url_for
from service.models import Product, Category, DataValidationError
from service.common import status
from . import app


######################################################################
# HEALTH CHECK
######################################################################
@app.route("/health")
def healthcheck():
    """Let them know our heart is still beating"""
    return jsonify(status=200, message="OK"), status.HTTP_200_OK


######################################################################
# HOME PAGE
######################################################################
@app.route("/")
def index():
    """Base URL for our service"""
    return app.send_static_file("index.html")


######################################################################
# UTILITY FUNCTIONS
######################################################################
def check_content_type(content_type):
    """Checks that the media type is correct"""
    if request.headers.get("Content-Type") != content_type:
        app.logger.error(
            "Invalid or missing Content-Type: %s",
            request.headers.get("Content-Type"),
        )
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )


def find_product_or_404(product_id):
    """Find a product by ID or return 404"""
    product = Product.find(product_id)
    if product is None:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Product with id '{product_id}' was not found.",
        )
    return product


def serialize_products(products):
    """Serialize a collection of products"""
    return [product.serialize() for product in products]


######################################################################
# CREATE A PRODUCT
######################################################################
@app.route("/products", methods=["POST"])
def create_products():
    """Create a Product"""
    app.logger.info("Request to create a Product")
    check_content_type("application/json")

    data = request.get_json()
    if not data:
        abort(status.HTTP_400_BAD_REQUEST, "Request body must be JSON.")

    try:
        product = Product()
        product.deserialize(data)
        product.create()
    except DataValidationError as error:
        abort(status.HTTP_400_BAD_REQUEST, str(error))

    location_url = url_for(
        "get_products",
        product_id=product.id,
        _external=True,
    )

    return (
        jsonify(product.serialize()),
        status.HTTP_201_CREATED,
        {"Location": location_url},
    )


######################################################################
# LIST AND FILTER PRODUCTS
######################################################################
@app.route("/products", methods=["GET"])
def list_products():
    """List all products, optionally filtering by query parameters"""
    products = Product.all()

    name = request.args.get("name")
    category = request.args.get("category")
    available = request.args.get("available")
    price = request.args.get("price")

    if name:
        products = Product.find_by_name(name)

    if category:
        try:
            category_value = Category[category.upper()]
        except KeyError:
            abort(
                status.HTTP_400_BAD_REQUEST,
                f"Invalid category: {category}",
            )
        products = Product.find_by_category(category_value)

    if available is not None:
        available_value = available.lower()
        if available_value not in ("true", "false"):
            abort(
                status.HTTP_400_BAD_REQUEST,
                "Available must be true or false.",
            )
        products = Product.find_by_availability(
            available_value == "true"
        )

    if price is not None:
        try:
            price_value = Decimal(price)
        except (InvalidOperation, ValueError):
            abort(
                status.HTTP_400_BAD_REQUEST,
                "Price must be a valid number.",
            )
        products = Product.find_by_price(price_value)

    return jsonify(serialize_products(products)), status.HTTP_200_OK


######################################################################
# READ A PRODUCT
######################################################################
@app.route("/products/<int:product_id>", methods=["GET"])
def get_products(product_id):
    """Read a single product by ID"""
    product = find_product_or_404(product_id)
    return jsonify(product.serialize()), status.HTTP_200_OK


######################################################################
# UPDATE A PRODUCT
######################################################################
@app.route("/products/<int:product_id>", methods=["PUT"])
def update_products(product_id):
    """Update a product by ID"""
    check_content_type("application/json")
    product = find_product_or_404(product_id)

    data = request.get_json()
    if not data:
        abort(status.HTTP_400_BAD_REQUEST, "Request body must be JSON.")

    try:
        product.deserialize(data)
        product.id = product_id
        product.update()
    except DataValidationError as error:
        abort(status.HTTP_400_BAD_REQUEST, str(error))

    return jsonify(product.serialize()), status.HTTP_200_OK


######################################################################
# DELETE A PRODUCT
######################################################################
@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_products(product_id):
    """Delete a product by ID"""
    product = find_product_or_404(product_id)
    product.delete()
    return "", status.HTTP_204_NO_CONTENT
