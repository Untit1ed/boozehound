import logging
from typing import Dict, List, Optional, Tuple

from src.db_helper import DbHelper # Corrected import

from src.models.country import Country # Corrected import


class CountryRepository:
    logger = logging.getLogger(__name__)
    def __init__(self, db_helper: DbHelper):
        """
        Initialize the CountryRepository with a DbHelper instance and load existing countries.

        :param db_helper: An instance of the DbHelper class.
        """
        self.db_helper = db_helper
        self.countries_map: Dict[str, Country] = self.load_countries()

    def load_countries(self) -> Dict[str, Country]:
        """
        Load all countries from the database into an in-memory dictionary.

        :return: A dictionary mapping Country objects to country IDs.
        """
        query = "SELECT name, code FROM countries"
        print('Loading countries from DB...', end='\r')
        countries = self.db_helper.execute_query(query)
        if not countries:
            return {}

        print(f'\x1b[2K\r{len(countries)} countries loaded.')
        return {code: Country(name=name, code=code) for name, code in countries}

    def get_or_add_country(self, country: Country) -> str:
        """
        Retrieve the country ID if it exists in memory; otherwise, insert the country into the database and return the new ID.

        :param name: The name of the country.
        :param code: The code of the country.
        :return: The code of the country.
        """
        # Check if the country is already in memory
        if country.code in self.countries_map:
            return country.code

        # Country is not in memory, so insert into the database
        insert_query = "INSERT INTO countries (name, code) VALUES (%s, %s)"
        new_id = self.db_helper.insert_query(insert_query, (country.name, country.code))

        # Update the in-memory dictionary
        self.countries_map[country.code] = country

        self.logger.info(f"{country} country was inserted with id {new_id}.")

        return country.code

    def bulk_add_countries(self, countries: List[Country]) -> None:
        """
        Bulk insert countries into the database and update the in-memory map.

        :param countries: A list of Country objects to insert.
        """
        new_countries_to_insert = [c for c in countries if c and c.code not in self.countries_map]

        if not new_countries_to_insert:
            self.logger.info("No new countries to insert.")
            return

        data_to_insert = [(country.name, country.code) for country in new_countries_to_insert]
        
        attempted_count = len(data_to_insert)
        self.logger.info(f"Attempting to insert {attempted_count} new countries.")

        try:
            insert_query = "INSERT INTO countries (name, code) VALUES (%s, %s)"
            self.db_helper.bulk_insert_query(insert_query, data_to_insert)

            # Update the in-memory dictionary for successfully inserted countries
            for country in new_countries_to_insert:
                self.countries_map[country.code] = country
            
            self.logger.info(f"Successfully inserted {len(new_countries_to_insert)} new countries.")

        except Exception as e:
            self.logger.error(f"Error during bulk insert of countries: {e}")
            # Depending on the DB behavior and DbHelper capabilities,
            # we might not know exactly which ones failed.
            # For now, we assume either all succeed or all fail with an exception.
            # A more robust solution might involve fetching existing countries again
            # or handling partial failures if the DbHelper could provide such info.
