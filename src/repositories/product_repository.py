from typing import Dict, Optional, List
import logging

from db_helper import DbHelper

from models.price_history import PriceHistory
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
        self.products_map: Dict[str, Product] = self.load_products()

    def load_products(self) -> Dict[str, Product]:
        """
        Load all products from the database into an in-memory dictionary.

        :return: A dictionary mapping Product objects to product IDs.
        """
        query = """SELECT
    p.sku, name, category_id, country_code, description, volume, alcohol, upc, unit_size, id, sub_category_id, class_id,
    last_updated, regular_price, current_price, promotion_start_date, promotion_end_date, last_update >= CURRENT_DATE - 2 as is_active, first_update
FROM products p
JOIN (
    SELECT sku, MAX(last_updated) as last_update, MIN(last_updated) as first_update
    FROM price_history
    WHERE last_updated >= CURRENT_DATE - 90
    GROUP BY sku
) h ON p.sku = h.sku
JOIN (
    SELECT sku, last_updated, regular_price, current_price, promotion_start_date, promotion_end_date
    FROM price_history
) ph ON p.sku = ph.sku AND h.last_update = ph.last_updated
"""

        print('Loading products from DB...', end='\r')
        products = self.db_helper.execute_query(query)
        if not products:
            return {}

        print(f'\x1b[2K\r{len(products) if products else 0} products loaded.')
        product_dict = {}

        for row in products:
            try:
                sku, name, category_id, country_code, description, volume, alcohol, upc, unit_size, id, sub_category_id, class_id, last_updated, regular_price, current_price, promotion_start_date, promotion_end_date, is_active, first_update = row

                if not sku or not name:
                    logging.warning(f"Skipping product with missing required fields: SKU={sku}, name={name}")
                    continue

                # Get category with error handling
                category = self.category_repository.categories_map.get(category_id)
                if not category and category_id:
                    logging.warning(f"Missing category {category_id} for product {sku}")

                # Get sub-category with error handling
                sub_category = self.category_repository.categories_map.get(sub_category_id)
                if not sub_category and sub_category_id:
                    logging.warning(f"Missing sub-category {sub_category_id} for product {sku}")

                # Get class with error handling
                class_name = self.category_repository.categories_map.get(class_id)
                if not class_name and class_id:
                    logging.warning(f"Missing class {class_id} for product {sku}")

                # Get country with error handling
                country = self.country_repository.countries_map.get(country_code)
                if not country and country_code:
                    logging.warning(f"Missing country {country_code} for product {sku}")

                history = PriceHistory(
                    sku=sku,
                    last_updated=last_updated,
                    regular_price=regular_price,
                    current_price=current_price,
                    promotion_start_date=promotion_start_date,
                    promotion_end_date=promotion_end_date
                )

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
                    #price_history=sorted(history, key=lambda x: x.last_updated) if history else None,
                    price_history=[history],
                    is_active=is_active,
                    first_update=first_update,
                )

                product_dict[product.sku] = product

            except Exception as e:
                logging.error(f"Error processing product row: {row}. Error: {str(e)}")
                continue

        print(f"Successfully loaded {len(product_dict)} valid products")
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
        if product.sku in self.products_map:
            return product.sku

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

        self.db_helper.insert_query(
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
        self.products_map[product.sku] = product

        print(f"{(product.name, product.sku, product.upc)} product was inserted.")

        return product.sku

    def bulk_add_products(self, products: List[Product]) -> None:
        """
        Bulk insert or update multiple products efficiently.

        :param products: List of products to insert or update
        """
        params_list = []
        processed_skus = set()

        for product in products:
            if not product.sku or not product.name:
                logging.warning(f"Skipping product with missing required fields: SKU={product.sku}, name={product.name}")
                continue

            # Skip if product already exists in memory
            if product.sku in processed_skus or product.sku in self.products_map:
                continue

            params_list.append((
                product.sku,
                product.name,
                self.category_repository.get_or_add_category(product.category),
                self.country_repository.get_or_add_country(product.country),
                product.tastingDescription,
                product.volume,
                product.alcoholPercentage,
                product.upc,
                product.unitSize,
                self.category_repository.get_or_add_category(product.subCategory),
                self.category_repository.get_or_add_category(product.subSubCategory)
            ))
            processed_skus.add(product.sku)

            # Update in-memory map
            self.products_map[product.sku] = product

        if not params_list:
            return None

        print(f'Inserting {len(params_list)} products...')

        if self.db_helper.is_mysql:
            insert_query = """
                INSERT INTO products (
                    sku, name, category_id, country_code, description,
                    volume, alcohol, upc, unit_size,
                    sub_category_id, class_id
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
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
                    sku, name, category_id, country_code, description,
                    volume, alcohol, upc, unit_size,
                    sub_category_id, class_id
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (sku)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    upc = EXCLUDED.upc,
                    category_id = EXCLUDED.category_id,
                    sub_category_id = EXCLUDED.sub_category_id,
                    class_id = EXCLUDED.class_id,
                    date_updated = NOW()
            """
        self.db_helper.bulk_insert_query(insert_query, params_list)
        print(f"Bulk inserted/updated {len(params_list)} products")
