from typing import Dict

from db_helper import DbHelper

from models.product import Product
from repositories.category_repository import CategoryRepository
from repositories.country_repository import CountryRepository
from repositories.price_history_repository import PriceHistoryRepository


class ProductRepository:
    def __init__(
        self,
        db_helper: DbHelper,
        category_repository: CategoryRepository,
        country_repository: CountryRepository,
        history_repository: PriceHistoryRepository,
    ):
        """
        Initialize the ProductRepository with a DbHelper instance and load existing products.

        :param db_helper: An instance of the DbHelper class.
        """
        self.db_helper = db_helper
        self.category_repository: CategoryRepository = category_repository
        self.country_repository: CountryRepository = country_repository
        self.history_repository: PriceHistoryRepository = history_repository
        self.products_map: Dict[Product, int] = self.load_products()

    def load_products(self) -> Dict[Product, int]:
        """
        Load all products from the database into an in-memory dictionary.

        :return: A dictionary mapping Product objects to product IDs.
        """
        query = """SELECT sku, name, category_id, country_code, description, volume, alcohol, upc, unit_size, id, sub_category_id, class_id
FROM products;"""

        print('Loading products from DB...', end='\r')
        products = self.db_helper.execute_query(query)
        print(f'\x1b[2K\r{len(products)} products loaded.')
        product_dict = {}

        for row in products:
            sku, name, category_id, country_code, description, volume, alcohol, upc, unit_size, id, sub_category_id, class_id = row

            category = self.category_repository.categories_map.get(category_id)
            sub_category = self.category_repository.categories_map.get(sub_category_id)
            class_name = self.category_repository.categories_map.get(class_id)
            country = self.country_repository.countries_map.get(country_code)
            history = self.history_repository.history_map.get(sku)

            product = Product(
                sku=sku,
                name=name,
                category=category,
                country=country,
                tastingDescription=description,
                volume=volume,
                alcoholPercentage=alcohol,
                upc=upc,
                unitSize=unit_size,
                subCategory=sub_category,
                subSubCategory=class_name,
                price_history=sorted(history, key=lambda x: x.last_updated) if history else None
            )

            product_dict[product] = id

        return product_dict

    def get_or_add_product(
        self,
        product: Product,
    ) -> int:
        """
        Retrieve the product ID if it exists in memory based on sku;
        otherwise, insert the product into the database and return the new ID.

        :param product: The product object.
        :return: The ID of the product.
        """

        # Check if the product is already in memory
        if product in self.products_map:
            return self.products_map[product]

        # Insert category into the database
        if self.db_helper.is_mysql:
            insert_query = """
                INSERT INTO products (
                    sku, name, category_id, country_code, description, volume, alcohol, upc, unit_size,
                    sub_category_id, class_id
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    id = LAST_INSERT_ID(id),
                    name = VALUES(name),
                    upc = VALUES(upc),
                    category_id = VALUES(category_id),
                    sub_category_id = VALUES(sub_category_id),
                    class_id = VALUES(class_id),
                    date_updated = now()
            """
        else:
            insert_query = """
                INSERT INTO products (
                    sku, name, category_id, country_code, description, volume, alcohol, upc, unit_size,
                    sub_category_id, class_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (sku)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    upc = EXCLUDED.upc,
                    category_id = EXCLUDED.category_id,
                    sub_category_id = EXCLUDED.sub_category_id,
                    class_id = EXCLUDED.class_id,
                    date_updated = NOW();
            """

        new_product_id = self.db_helper.insert_query(
            insert_query,
            (
                product.sku, product.name, self.category_repository.get_or_add_category(product.category),
                self.country_repository.get_or_add_country(product.country), product.tastingDescription, product.volume,
                product.alcoholPercentage, product.upc, product.unitSize,
                self.category_repository.get_or_add_category(product.subCategory),
                self.category_repository.get_or_add_category(product.subSubCategory)
            )
        )

        # Update the in-memory dictionary
        self.products_map[product] = product.upc

        print(f"{(product.name, product.sku, product.upc)} product was inserted with id {new_product_id}.")

        return new_product_id
