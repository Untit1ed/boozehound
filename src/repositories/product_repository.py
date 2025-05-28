import logging
from typing import Dict, List, Optional

from src.db_helper import DbHelper # Corrected import

from src.models.price_history import PriceHistory # Corrected import
from src.models.product import Product # Corrected import
from src.repositories.category_repository import CategoryRepository # Corrected import
from src.repositories.country_repository import CountryRepository # Corrected import
from src.repositories.price_history_repository import PriceHistoryRepository # Corrected import

logger = logging.getLogger(__name__)

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
WHERE h.last_update >= CURRENT_DATE - 30
"""

        logger.debug('Loading products from DB...')
        products = self.db_helper.execute_query(query)
        if not products:
            logger.info("No products found in DB during load_products.")
            return {}

        logger.info(f'{len(products) if products else 0} product rows initially loaded from DB.')
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

        logger.info(f"Successfully loaded and processed {len(product_dict)} valid products into products_map.")
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
            return product.sku # Assuming SKU is used as ID here, or this should return an actual ID if available

        # Insert product into the database
        # Adjusted to use self.db_helper.db_type
        if self.db_helper.db_type == 'mysql':
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

        logger.info(f"Product {(product.name, product.sku, product.upc)} was inserted.")

        return product.sku # Assuming SKU is used as ID here

    def bulk_add_products(self, products: List[Product]) -> None:
        """
        Bulk insert or update multiple products efficiently.

        :param products: List of products to insert or update
        """
        if not products:
            logger.debug("No products provided for bulk add.")
            return None

        # Phase 1: Collect Unique Entities & Pre-process
        logger.debug("Starting pre-processing for bulk_add_products.")

        # Pre-process countries
        unique_countries = {prod.country for prod in products if prod.country}
        if unique_countries:
            logger.info(f"Found {len(unique_countries)} unique countries to pre-process.")
            self.country_repository.bulk_add_countries(list(unique_countries))
        
        # Pre-process category hierarchies
        unique_category_hierarchies = set()
        for prod in products:
            # Add hierarchy tuple: (main_cat, sub_cat, class_cat)
            # Ensure None is used if a category level is missing
            main_cat = prod.category
            sub_cat = prod.subCategory if main_cat else None # sub only relevant if main exists
            class_cat = prod.subSubCategory if main_cat and sub_cat else None # class only if main & sub exist
            
            if main_cat: # Only process if there's at least a main category
                 unique_category_hierarchies.add((main_cat, sub_cat, class_cat))

        if unique_category_hierarchies:
            logger.info(f"Found {len(unique_category_hierarchies)} unique category hierarchies to pre-process.")
            for main_cat, sub_cat, class_cat in unique_category_hierarchies:
                # The get_or_add_category expects the most specific category first.
                # All parameters must be Category objects or None.
                if class_cat: # If class_cat (most specific) exists
                    self.category_repository.get_or_add_category(
                        category=class_cat, 
                        parent_category=sub_cat,       # sub_cat must exist if class_cat exists as per Product model logic
                        grandparent_category=main_cat  # main_cat must exist if class_cat exists
                    )
                elif sub_cat: # If no class_cat, but sub_cat exists
                    self.category_repository.get_or_add_category(
                        category=sub_cat, 
                        parent_category=main_cat,      # main_cat must exist if sub_cat exists
                        grandparent_category=None
                    )
                elif main_cat: # If only main_cat exists
                    self.category_repository.get_or_add_category(
                        category=main_cat, 
                        parent_category=None, 
                        grandparent_category=None
                    )
        
        logger.debug("Finished pre-processing.")

        # Phase 2: Product Parameter Preparation Loop
        params_list = []
        processed_skus = set() 

        for product in products:
            if not product.sku or not product.name:
                logging.warning(f"Skipping product with missing required fields: SKU={product.sku}, name={product.name}")
                continue

            # Skip if product SKU has already been processed in this batch 
            # (self.products_map check for existing products in DB is implicitly handled by ON CONFLICT/DUPLICATE KEY)
            if product.sku in processed_skus:
                continue
            
            # These calls should now primarily hit the cache due to pre-processing
            country_code_val = self.country_repository.get_or_add_country(product.country) if product.country else None
            
            main_cat_id = None
            sub_cat_id = None
            class_cat_id = None

            if product.category:
                main_cat_id = self.category_repository.get_or_add_category(product.category)
                if product.subCategory:
                    sub_cat_id = self.category_repository.get_or_add_category(product.subCategory, parent_category=product.category)
                    if product.subSubCategory:
                        class_cat_id = self.category_repository.get_or_add_category(product.subSubCategory, parent_category=product.subCategory, grandparent_category=product.category)
            
            params_list.append((
                product.sku,
                product.name,
                main_cat_id,
                country_code_val,
                product.tastingDescription,
                product.volume,
                product.alcoholPercentage,
                product.upc,
                product.unitSize,
                sub_cat_id,
                class_cat_id
            ))
            processed_skus.add(product.sku)

            # Update in-memory map for newly processed products in this batch
            # Note: self.products_map should ideally be updated after successful DB operation,
            # or if the product was skipped due to already being in products_map (meaning it's from DB load).
            # For this refactor, we'll keep the existing logic of updating it here for products processed in this batch.
            if product.sku not in self.products_map:
                 self.products_map[product.sku] = product


        if not params_list:
            logger.debug("No new products to bulk insert after filtering processed SKUs.")
            return None

        logger.info(f'Bulk inserting/updating {len(params_list)} products...')

        # Adjusted to use self.db_helper.db_type
        if self.db_helper.db_type == 'mysql':
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
        logger.info(f"Bulk inserted/updated {len(params_list)} products")
