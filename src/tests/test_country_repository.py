import unittest
from unittest.mock import patch, MagicMock, call

# Assuming PYTHONPATH is set to /app for src. imports
from src.models.country import Country
from src.repositories.country_repository import CountryRepository
from src.db_helper import DbHelper # Needed for type hinting if not already imported by repo

class TestCountryRepository(unittest.TestCase):

    def setUp(self):
        # Mock the logger used in CountryRepository (it's a class variable)
        self.patcher_logger = patch('src.repositories.country_repository.CountryRepository.logger')
        self.mock_logger = self.patcher_logger.start()

        # Create a mock DbHelper instance
        self.mock_db_helper = MagicMock(spec=DbHelper)
        
        # Mock the return value of load_countries during CountryRepository instantiation
        # to avoid actual DB calls or errors if execute_query is not fully mocked.
        # This allows us to control the initial state of countries_map.
        with patch.object(CountryRepository, 'load_countries', return_value={}) as mock_load_countries:
            self.repository = CountryRepository(db_helper=self.mock_db_helper)
        
        # Ensure the map is what we expect after mocking load_countries
        self.repository.countries_map = {}


    def tearDown(self):
        self.patcher_logger.stop()

    def test_bulk_add_countries_new_countries(self):
        new_countries = [
            Country(name="Newland", code="NL"),
            Country(name="Freshland", code="FL")
        ]
        
        self.repository.bulk_add_countries(new_countries)

        expected_data_to_insert = [("Newland", "NL"), ("Freshland", "FL")]
        self.mock_db_helper.bulk_insert_query.assert_called_once_with(
            "INSERT INTO countries (name, code) VALUES (%s, %s)",
            expected_data_to_insert
        )
        self.assertIn("NL", self.repository.countries_map)
        self.assertEqual(self.repository.countries_map["NL"].name, "Newland")
        self.assertIn("FL", self.repository.countries_map)
        self.assertEqual(self.repository.countries_map["FL"].name, "Freshland")
        self.mock_logger.info.assert_any_call(f"Attempting to insert {len(expected_data_to_insert)} new countries.")
        self.mock_logger.info.assert_any_call(f"Successfully inserted {len(new_countries)} new countries.")

    def test_bulk_add_countries_existing_countries(self):
        # Pre-populate the map
        existing_country = Country(name="Oldland", code="OL")
        self.repository.countries_map = {"OL": existing_country}
        
        countries_to_add = [Country(name="Oldland", code="OL")] # Try to add the same country
        
        self.repository.bulk_add_countries(countries_to_add)
        
        self.mock_db_helper.bulk_insert_query.assert_not_called()
        self.mock_logger.info.assert_called_with("No new countries to insert.")
        self.assertEqual(len(self.repository.countries_map), 1) # Size should not change

    def test_bulk_add_countries_mixed_new_and_existing(self):
        existing_country = Country(name="Oldland", code="OL")
        self.repository.countries_map = {"OL": existing_country}
        
        countries_to_add = [
            Country(name="Oldland", code="OL"), # Existing
            Country(name="Newland", code="NL")  # New
        ]
        
        self.repository.bulk_add_countries(countries_to_add)
        
        expected_data_to_insert = [("Newland", "NL")]
        self.mock_db_helper.bulk_insert_query.assert_called_once_with(
            "INSERT INTO countries (name, code) VALUES (%s, %s)",
            expected_data_to_insert
        )
        self.assertIn("OL", self.repository.countries_map)
        self.assertIn("NL", self.repository.countries_map)
        self.assertEqual(self.repository.countries_map["NL"].name, "Newland")
        self.assertEqual(len(self.repository.countries_map), 2)
        self.mock_logger.info.assert_any_call(f"Attempting to insert 1 new countries.") # Only one new country
        self.mock_logger.info.assert_any_call(f"Successfully inserted 1 new countries.")


    def test_bulk_add_countries_empty_list(self):
        self.repository.bulk_add_countries([])
        
        self.mock_db_helper.bulk_insert_query.assert_not_called()
        self.mock_logger.info.assert_called_with("No new countries to insert.")

    def test_bulk_add_countries_with_none_in_list(self):
        # Test robustness against None values in the input list
        countries_to_add = [
            Country(name="Validland", code="VL"),
            None, 
            Country(name="AnotherValid", code="AV")
        ]
        
        # Casting countries_to_add to List[Country] for type checker, though it contains None
        self.repository.bulk_add_countries(countries_to_add) 
        
        expected_data_to_insert = [("Validland", "VL"), ("AnotherValid", "AV")]
        self.mock_db_helper.bulk_insert_query.assert_called_once_with(
            "INSERT INTO countries (name, code) VALUES (%s, %s)",
            expected_data_to_insert
        )
        self.assertIn("VL", self.repository.countries_map)
        self.assertIn("AV", self.repository.countries_map)
        self.assertEqual(len(self.repository.countries_map), 2)

    def test_bulk_add_countries_db_exception(self):
        new_countries = [Country(name="ErrorLand", code="EL")]
        self.mock_db_helper.bulk_insert_query.side_effect = Exception("DB error")

        # Current behavior: CountryRepository.bulk_add_countries logs the error but does not re-raise.
        self.repository.bulk_add_countries(new_countries)
        
        self.mock_logger.error.assert_called_once_with("Error during bulk insert of countries: DB error")
        # Map update happens after DB call; if DB call fails, map shouldn't be updated.
        self.assertNotIn("EL", self.repository.countries_map)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
