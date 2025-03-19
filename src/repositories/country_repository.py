from typing import Dict, Optional, Tuple

from db_helper import DbHelper

from models.country import Country


class CountryRepository:
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

        print(f"{country} country was inserted with id {new_id}.")

        return country.code
