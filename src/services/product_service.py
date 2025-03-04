
import json
from typing import List

from db_helper import DbHelper

from models.product import Product
from repositories.category_repository import CategoryRepository
from repositories.country_repository import CountryRepository
from repositories.price_history_repository import PriceHistoryRepository
from repositories.product_repository import ProductRepository


class ProductService:
    def __init__(self, db_url: str, load_repos: bool = False) -> None:
        if db_url == 'localhost':
            self.db_config = {
                'host': db_url,
                'user': 'cron_job',
                'password': 'cron_job123$',
                'database': 'bcl',
            }
        elif db_url == 'untit1ed.mysql.pythonanywhere-services.com':
            self.db_config = {
                'host': db_url,
                'user': 'untit1ed',
                'password': 'cron_job123$',
                'database': 'bcl',
            }
        else:
            self.db_config = {
                'host': db_url,
                'user': 'cron_job',
                'password': 'Jz2cKk1tRiEj',
                'dbname': 'bcl',
            }


        self.products: List[Product] = []

        if load_repos:
            self.load_repos()

    def load_repos(self) -> None:
        db_helper = DbHelper(self.db_config)
        self.country_repo = CountryRepository(db_helper)
        self.category_repo = CategoryRepository(db_helper)
        self.price_history_repo = PriceHistoryRepository(db_helper)

        self.product_repo = ProductRepository(db_helper, self.category_repo, self.country_repo, self.price_history_repo)

        self.products = sorted(list(self.product_repo.products_map.values()),
                               key=lambda p: p.combined_score(), reverse=True)

    def load_products(self, filename: str) -> None:
        with open(filename, 'r', encoding="utf8") as file:
            json_data = json.load(file)

        hits = json_data.get("hits", {}).get("hits", [])

        products = [Product(**hit.get("_source", {})) for hit in hits]

        # Sort products by the custom metric
        self.products = sorted(products, key=lambda p: p.combined_score(), reverse=True)

    def persist_products(self):
        for country in {product.country for product in self.products if product.country is not None}:
            self.country_repo.get_or_add_country(country)

        categories = {(product.category, product.subCategory, product.subSubCategory) for product in self.products}
        for category, subCategory, subSubCategory in categories:
            if category:
                self.category_repo.get_or_add_category(
                    subSubCategory,
                    subCategory,
                    category
                )

        for product in self.products:
            self.product_repo.get_or_add_product(product)
            # self.price_history_repo.get_or_add_price_history(product)

        self.price_history_repo.bulk_add_price_histories(self.products)  # Add this instead of the loop
