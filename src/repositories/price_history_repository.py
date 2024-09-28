from typing import Dict, List

from dateutil import parser
from db_helper import DbHelper

from models.price_history import PriceHistory


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
    last_updated, upc, sku, regular_price, current_price, promotion_start_date, promotion_end_date, source
FROM price_history;"""

        print('Loading price histories from DB...', end='\r')
        price_histories = self.db_helper.execute_query(query)
        print(f'\x1b[2K\r{len(price_histories)} price histories loaded.')

        price_history_dict = {}

        for row in price_histories:
            last_updated, upc, sku, regular_price, current_price, promotion_start_date, promotion_end_date, source = row

            history = PriceHistory(
                upc=upc,
                sku=sku,
                last_updated=last_updated,
                regular_price=regular_price,
                current_price=current_price,
                promotion_start_date=promotion_start_date,
                promotion_end_date=promotion_end_date
            )

            price_history_dict.setdefault(upc, []).append(history)

        return price_history_dict

    def get_or_add_price_history(
        self,
        history: PriceHistory,
    ) -> str:
        """
        Retrieve the history ID if it exists in memory based on upc;
        otherwise, insert the history into the database and return the new ID.

        :param history: The history object.
        :return: The ID of the product.
        """

        # Check if the history is already in memory
        if history.upc in self.history_map and history in self.history_map[history.upc]:
            return history.upc

        # Insert category into the database
        insert_query = """
            INSERT INTO price_history (
                last_updated, upc, sku, regular_price, current_price, promotion_start_date, promotion_end_date, source
            ) VALUES(%s, %s, %s, %s, %s, %s, %s, 'bcl');
        """
        new_id = self.db_helper.insert_query(
            insert_query,
            (
                history.last_updated, history.upc, history.sku, history.regular_price, history.current_price,
                history.promotion_start_date,
                history.promotion_end_date
            )
        )

        # Update the in-memory dictionary
        self.history_map.setdefault(history.upc, []).append(history)

        print(f"{(history.upc)} history was inserted with id {new_id}.")

        return history.upc

    def convert_to_date(elf, datetime_string):
        if datetime_string is None:
            return None
        try:
            # Convert string to datetime object and then to date object
            date_object = parser.parse(datetime_string).date()
            return date_object
        except (ValueError, TypeError):
            # Handle invalid datetime strings or other exceptions
            print("Invalid datetime string")
            return None
