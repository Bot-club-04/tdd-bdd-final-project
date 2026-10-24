
######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
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
Product API Service Test Suite

Test cases can be run with:
    nosetests -v
    coverage report -m
"""

import os
import logging
from decimal import Decimal
from unittest import TestCase

from service import app
from service.common import status
from service.models import db, init_db, Product
from tests.factories import ProductFactory


DATABASE_URI = os.getenv(
    "DATABASE_URI",
    "postgresql://postgres:postgres@localhost:5432/postgres",
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()
        db.session.commit()

    def tearDown(self):
        """Runs after each test"""
        db.session.remove()

    ##################################################################
    # Utility function to bulk create products
    ##################################################################
    def _create_products(self, count=1):
        """Create products through the API"""
        products = []

        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(
                BASE_URL,
                json=test_product.serialize(),
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test product",
            )

            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)

        return products

    ##################################################################
    # INDEX AND HEALTH
    ##################################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            b"Product Catalog Administration",
            response.data,
        )

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["message"], "OK")

    ##################################################################
    # CREATE
    ##################################################################
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()

        response = self.client.post(
            BASE_URL,
            json=test_product.serialize(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        location = response.headers.get("Location")
        self.assertIsNotNone(location)

        new_product = response.get_json()

        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(
            new_product["description"],
            test_product.description,
        )
        self.assertEqual(
            Decimal(new_product["price"]),
            test_product.price,
        )
        self.assertEqual(
            new_product["available"],
            test_product.available,
        )
        self.assertEqual(
            new_product["category"],
            test_product.category.name,
        )

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]

        response = self.client.post(BASE_URL, json=new_product)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_product_no_content_type(self):
        """It should reject a request without Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")

        self.assertEqual(
            response.status_code,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    def test_create_product_wrong_content_type(self):
        """It should reject the wrong Content-Type"""
        response = self.client.post(
            BASE_URL,
            data="bad data",
            content_type="plain/text",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    ##################################################################
    # READ
    ##################################################################
    def test_get_product(self):
        """It should Read a single Product"""
        test_product = self._create_products()[0]

        response = self.client.get(
            f"{BASE_URL}/{test_product.id}"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.get_json()

        self.assertEqual(data["id"], test_product.id)
        self.assertEqual(data["name"], test_product.name)
        self.assertEqual(
            data["description"],
            test_product.description,
        )
        self.assertEqual(
            Decimal(data["price"]),
            test_product.price,
        )
        self.assertEqual(
            data["available"],
            test_product.available,
        )
        self.assertEqual(
            data["category"],
            test_product.category.name,
        )

    def test_get_product_not_found(self):
        """It should return 404 for a missing Product"""
        response = self.client.get(f"{BASE_URL}/0")

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    ##################################################################
    # UPDATE
    ##################################################################
    def test_update_product(self):
        """It should Update an existing Product"""
        test_product = self._create_products()[0]

        updated_data = test_product.serialize()
        updated_data["description"] = "Updated product description"
        updated_data["price"] = "29.99"

        response = self.client.put(
            f"{BASE_URL}/{test_product.id}",
            json=updated_data,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        # Read the product back to verify the update
        response = self.client.get(
            f"{BASE_URL}/{test_product.id}"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.get_json()
        self.assertEqual(
            data["description"],
            "Updated product description",
        )
        self.assertEqual(Decimal(data["price"]), Decimal("29.99"))

    def test_update_product_not_found(self):
        """It should return 404 when updating a missing Product"""
        product = ProductFactory().serialize()

        response = self.client.put(
            f"{BASE_URL}/0",
            json=product,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    ##################################################################
    # DELETE
    ##################################################################
    def test_delete_product(self):
        """It should Delete a Product"""
        test_product = self._create_products()[0]

        response = self.client.delete(
            f"{BASE_URL}/{test_product.id}"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        # Verify the product is no longer available
        response = self.client.get(
            f"{BASE_URL}/{test_product.id}"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_delete_product_not_found(self):
        """It should return 404 when deleting a missing Product"""
        response = self.client.delete(f"{BASE_URL}/0")

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    ##################################################################
    # LIST ALL PRODUCTS
    ##################################################################
    def test_list_products(self):
        """It should List all Products"""
        self._create_products(3)

        response = self.client.get(BASE_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.get_json()
        self.assertEqual(len(data), 3)

    def test_list_products_empty(self):
        """It should return an empty list when no Products exist"""
        response = self.client.get(BASE_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.get_json(), [])

    ##################################################################
    # FILTER BY NAME
    ##################################################################
    def test_query_products_by_name(self):
        """It should filter Products by name"""
        test_product = self._create_products()[0]

        response = self.client.get(
            BASE_URL,
            query_string={"name": test_product.name},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.get_json()
        self.assertGreaterEqual(len(data), 1)
        self.assertTrue(
            any(product["name"] == test_product.name for product in data)
        )

    ##################################################################
    # FILTER BY CATEGORY
    ##################################################################
    def test_query_products_by_category(self):
        """It should filter Products by category"""
        test_product = self._create_products()[0]

        response = self.client.get(
            BASE_URL,
            query_string={
                "category": test_product.category.name,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.get_json()
        self.assertGreaterEqual(len(data), 1)

        for product in data:
            self.assertEqual(
                product["category"],
                test_product.category.name,
            )

    ##################################################################
    # FILTER BY AVAILABILITY
    ##################################################################
    def test_query_products_by_availability(self):
        """It should filter Products by availability"""
        test_product = self._create_products()[0]

        response = self.client.get(
            BASE_URL,
            query_string={
                "available": str(test_product.available).lower(),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.get_json()
        self.assertGreaterEqual(len(data), 1)

        for product in data:
            self.assertEqual(
                product["available"],
                test_product.available,
            )

    def test_query_products_by_price(self):
        """It should filter Products by price"""
        test_product = self._create_products()[0]

        response = self.client.get(
            BASE_URL,
            query_string={"price": str(test_product.price)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertTrue(
            any(
                Decimal(product["price"]) == test_product.price
                for product in data
            )
        )

    def test_query_products_by_invalid_category(self):
        """It should reject an invalid category"""
        response = self.client.get(
            BASE_URL,
            query_string={"category": "INVALID_CATEGORY"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_query_products_by_invalid_availability(self):
        """It should reject an invalid availability value"""
        response = self.client.get(
            BASE_URL,
            query_string={"available": "sometimes"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_query_products_by_invalid_price(self):
        """It should reject an invalid price"""
        response = self.client.get(
            BASE_URL,
            query_string={"price": "not-a-number"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_update_product_no_content_type(self):
        """It should reject an update without JSON Content-Type"""
        test_product = self._create_products()[0]

        response = self.client.put(
            f"{BASE_URL}/{test_product.id}",
            data="bad data",
            content_type="text/plain",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    def test_update_product_invalid_data(self):
        """It should reject an update missing a required field"""
        test_product = self._create_products()[0]
        updated_data = test_product.serialize()
        del updated_data["name"]

        response = self.client.put(
            f"{BASE_URL}/{test_product.id}",
            json=updated_data,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_method_not_allowed(self):
        """It should return 405 for an unsupported HTTP method"""
        response = self.client.post(f"{BASE_URL}/1", json={})

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    ##################################################################
    # Utility functions
    ##################################################################

    def get_product_count(self):
        """Return the current number of Products"""
        response = self.client.get(BASE_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.get_json()
        return len(data)
