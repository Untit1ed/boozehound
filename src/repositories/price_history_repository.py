from typing import Dict, List, Optional, Set
import logging

from db_helper import DbHelper

from models.price_history import PriceHistory
from models.product import Product


class PriceHistoryRepository:
    def __init__(
        self,
        db_helper: DbHelper,
    ):

        """
        Initialize the PriceHistoryRepository with a DbHelper instance and load existing product histories.

        :param db_helper: An instance of the DbHelper class.
        """
        self.db_helper = db_helper
        self.history_map: Dict[str, List[PriceHistory]] = self.load_history()

    def load_history(self) -> Dict[str, List[PriceHistory]]:

        """
        Load all products price histories from the database into an in-memory dictionary.

        :return: A dictionary mapping PriceHistory objects to product IDs.
        """
        query = """SELECT
    last_updated, sku, regular_price, current_price, promotion_start_date, promotion_end_date
FROM price_history
WHERE last_updated >= CURRENT_DATE - 14;"""

        print('Loading price histories from DB...', end='\r')
        price_histories = self.db_helper.execute_query(query)
        print(f'\x1b[2K\r{len(price_histories)} price histories loaded.')

        price_history_dict = {}

        for row in price_histories:
            last_updated, sku, regular_price, current_price, promotion_start_date, promotion_end_date = row

            history = PriceHistory(
                sku=sku,
                last_updated=last_updated,
                regular_price=regular_price,
                current_price=current_price,
                promotion_start_date=promotion_start_date,
                promotion_end_date=promotion_end_date
            )

            price_history_dict.setdefault(sku, []).append(history)

        return price_history_dict

    def get_or_add_price_history(
        self,
        product: Product,
    ) -> Optional[str]:
        """
        Retrieve the history ID if it exists in memory based on sku;
        otherwise, insert the history into the database and return the new ID.

        :param product: The product object with price history.
        :return: The ID of the product, or None if price history is missing.
        """
        if not product.price_history:
            logging.warning(f"No price history found for product {product.sku}")
            return None

        try:
            history = product.price_history[-1]
        except IndexError:
            logging.warning(f"Empty price history list for product {product.sku}")
            return None

        # Check if the history is already in memory
        if history.sku in self.history_map and history in self.history_map[history.sku]:
            return history.sku

        # Insert price history into the database
        insert_query = """
            INSERT INTO price_history (
                last_updated, sku, regular_price, current_price, promotion_start_date, promotion_end_date, source
            ) VALUES(%s, %s, %s, %s, %s, %s, 'bcl');
        """
        self.db_helper.insert_query(
            insert_query,
            (
                history.last_updated, history.sku, history.regular_price, history.current_price,
                history.promotion_start_date,
                history.promotion_end_date
            )
        )

        # Update the in-memory dictionary
        self.history_map.setdefault(history.sku, []).append(history)

        logging.info(f"Price history inserted for product {product.name}")
        return history.sku

    def bulk_add_price_histories(self, products: List[Product]) -> None:
        """
        Bulk insert price histories for multiple products.

        :param products: List of products with price histories to insert.
        """
        params_list = []
        processed_histories: Set[tuple] = set()

        for product in products:
            if not product.price_history:
                continue

            history = product.price_history[-1]
            history_key = (history.sku, history.last_updated)

            # Skip if history already exists in memory or was already processed
            if (history.sku in self.history_map and history in self.history_map[history.sku]) or \
               history_key in processed_histories:
                continue

            params_list.append((
                history.last_updated, history.sku, history.regular_price,
                history.current_price, history.promotion_start_date,
                history.promotion_end_date, 'bcl'
            ))
            processed_histories.add(history_key)

            # Update in-memory map
            self.history_map.setdefault(history.sku, []).append(history)

        if params_list:
            insert_query = """
                INSERT INTO price_history (
                    last_updated, sku, regular_price, current_price,
                    promotion_start_date, promotion_end_date, source
                ) VALUES(%s, %s, %s, %s, %s, %s, %s);
            """
            self.db_helper.bulk_insert_query(insert_query, params_list)
            logging.info(f"Bulk inserted {len(params_list)} price histories")
