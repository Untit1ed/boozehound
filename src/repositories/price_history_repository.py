import logging
from itertools import groupby
from operator import itemgetter
from typing import Dict, List, Optional, Set, Tuple

from src.db_helper import DbHelper # Corrected import

from src.models.price_history import PriceHistory # Corrected import
from src.models.product import Product # Corrected import

logger = logging.getLogger(__name__)

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
        self.history_map: Dict[str, List[PriceHistory]] = {}

    def load_history(self, sku) -> List[PriceHistory]:

        """
        Load all products price histories from the database into an in-memory dictionary.

        :return: A dictionary mapping PriceHistory objects to product IDs.
        """
        query = """SELECT
    last_updated, sku, regular_price, current_price, promotion_start_date, promotion_end_date
FROM price_history WHERE sku = %s ORDER BY last_updated;"""

        logger.debug(f'Loading price histories from DB for sku {sku}...')
        price_histories = self.db_helper.execute_query(query, (sku,))
        if not price_histories:
            return []

        logger.info(f'{len(price_histories) if price_histories else 0} price histories loaded for sku {sku}.')

        price_histories_list = []

        for row in self.filter_prices(price_histories):
            last_updated, sku, regular_price, current_price, promotion_start_date, promotion_end_date = row

            history = PriceHistory(
                sku=sku,
                last_updated=last_updated,
                regular_price=regular_price,
                current_price=current_price,
                promotion_start_date=promotion_start_date,
                promotion_end_date=promotion_end_date
            )

            price_histories_list.append(history)

        self.history_map[sku] = price_histories_list
        return price_histories_list

    def filter_prices(self, prices: List[Tuple]) -> List[Tuple]:
        """
        Filter price history to keep only records where price changes occur.
        Groups by SKU first, then identifies price change points.

        :param prices: List of price history tuples (last_updated, sku, regular_price, current_price, promo_start, promo_end)
        :return: Filtered list containing only price change events and boundary points
        """
        if len(prices) < 2:
            return prices

        # Sort by SKU and date
        sorted_prices = sorted(prices, key=lambda x: (x[1], x[0]))  # sort by sku, then date
        filtered_prices = []

        # Group by SKU
        for sku, sku_group in groupby(sorted_prices, key=itemgetter(1)):
            sku_prices = list(sku_group)

            if not sku_prices:
                continue

            # Always keep the first and last price points for each SKU
            filtered_prices.append(sku_prices[0])

            # Add points where price changes
            for i in range(1, len(sku_prices)):
                curr_price = sku_prices[i][3]  # current_price is at index 3
                prev_price = sku_prices[i-1][3]

                if curr_price != prev_price:
                    # Add both the last price before change and first price after change
                    filtered_prices.append(sku_prices[i-1])
                    filtered_prices.append(sku_prices[i])

            # Add last price point if not already added
            if sku_prices[-1] not in filtered_prices:
                filtered_prices.append(sku_prices[-1])

        # Sort final result by date for chronological order
        return sorted(filtered_prices, key=itemgetter(0))

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

        logger.info(f"Price history inserted for product {product.name} (SKU: {product.sku})")
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

        if not params_list:
            logger.debug("No new price histories to bulk insert.")
            return None # Keep existing behavior of returning None

        logger.info(f'Inserting {len(params_list)} price histories...')

        insert_query = """
            INSERT INTO price_history (
                last_updated, sku, regular_price, current_price,
                promotion_start_date, promotion_end_date, source
            ) VALUES(%s, %s, %s, %s, %s, %s, %s);
        """
        self.db_helper.bulk_insert_query(insert_query, params_list)
        logger.info(f"Bulk inserted {len(params_list)} price histories")
