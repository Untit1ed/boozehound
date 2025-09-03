
import json
import logging
import os
from typing import List

from src.db_helper import DbHelper # Corrected import

from src.models.product import Product # Corrected import
from src.repositories.category_repository import CategoryRepository # Corrected import
from src.repositories.country_repository import CountryRepository # Corrected import
from src.repositories.price_history_repository import PriceHistoryRepository # Corrected import
from src.repositories.product_repository import ProductRepository # Corrected import


class ProductService:
    logger = logging.getLogger(__name__)

    def __init__(self, db_url: str, load_repos: bool = False) -> None:
        db_host = os.getenv('DB_HOST', db_url)
        db_user = os.getenv('DB_USER', 'cron_job')
        db_password = os.getenv('DB_PASSWORD', 'cron_job123$')
        db_name = os.getenv('DB_NAME', 'bcl')

        self.db_config = {
            'host': db_host,
            'user': db_user,
            'password': db_password,
            'database': db_name,
        }

        self.products: List[Product] = []

        if load_repos:
            self.load_repos()

    def load_repos(self) -> None:
        # DbHelper is now instantiated and stored as an instance variable
        self.db_helper = DbHelper(self.db_config) 
        self.country_repo = CountryRepository(self.db_helper)
        self.category_repo = CategoryRepository(self.db_helper)
        self.price_history_repo = PriceHistoryRepository(self.db_helper)

        self.product_repo = ProductRepository(self.db_helper, self.category_repo, self.country_repo, self.price_history_repo)

        self.products = sorted(list(self.product_repo.products_map.values()),
                               key=lambda p: p.combined_score(), reverse=True)

    def close(self) -> None:
        """
        Closes the database connection helper if it exists.
        """
        if hasattr(self, 'db_helper') and self.db_helper:
            self.logger.info("Closing ProductService's DbHelper connection.")
            self.db_helper.close()
        else:
            self.logger.debug("ProductService's DbHelper not found or already None.")

    def load_products(self, filename: str) -> None:
        self.products = []  # Initialize products to empty list
        try:
            with open(filename, 'r', encoding="utf8") as file:
                json_data = json.load(file)

            hits = json_data.get("hits", {}).get("hits", [])
            products = [Product(**hit.get("_source", {})) for hit in hits]
            # Sort products by the custom metric
            self.products = sorted(products, key=lambda p: p.combined_score(), reverse=True)

        except FileNotFoundError:
            self.logger.error(f"Error loading products: File not found - {filename}")
            # self.products is already []
        except json.JSONDecodeError:
            self.logger.error(f"Error loading products: Could not decode JSON from file - {filename}")
            # self.products is already []

    def persist_products(self):
        unique_countries = list({product.country for product in self.products if product.country is not None})
        if unique_countries:
            self.country_repo.bulk_add_countries(unique_countries)

        categories = {(product.category, product.subCategory, product.subSubCategory) for product in self.products}
        for category, subCategory, subSubCategory in categories:
            if category:
                self.category_repo.get_or_add_category(
                    subSubCategory,
                    subCategory,
                    category
                )

        self.product_repo.bulk_add_products(self.products)
        self.price_history_repo.bulk_add_price_histories(self.products)

    def reload_products(self):
        """Reload just the product repository and products from the database."""
        self.product_repo = ProductRepository(
            DbHelper(self.db_config),
            self.category_repo,
            self.country_repo,
            self.price_history_repo
        )
        self.products = sorted(list(self.product_repo.products_map.values()),
                             key=lambda p: p.combined_score(), reverse=True)
