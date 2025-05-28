import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import json
import os

# Assuming PYTHONPATH is set to /app
from src.services.product_service import ProductService
from src.models.product import Product
from src.models.country import Country 
from src.models.category import Category
# Import actual repository classes for spec, they will be mocked
from src.db_helper import DbHelper
from src.repositories.country_repository import CountryRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.price_history_repository import PriceHistoryRepository
from src.repositories.product_repository import ProductRepository

# Helper for os.getenv mocking
class _UnsetMarker: pass
UNSET_MARKER = _UnsetMarker()

class TestProductService(unittest.TestCase):

    def setUp(self):
        # Mock logger for ProductService (it's a class variable)
        self.patcher_logger = patch('src.services.product_service.ProductService.logger')
        self.mock_logger = self.patcher_logger.start()

        # Mock os.getenv for DB config
        # Default to UNSET_MARKER for all DB specific keys, can be overridden in tests
        self.getenv_mock_values = { 
            'DB_HOST': UNSET_MARKER, 'DB_USER': UNSET_MARKER, 
            'DB_PASSWORD': UNSET_MARKER, 'DB_NAME': UNSET_MARKER
        }

        def mock_getenv_logic(key, default_val_passed_to_getenv=None):
            val = self.getenv_mock_values.get(key, UNSET_MARKER)
            if val is not UNSET_MARKER: # Key is mocked, return its value (could be None)
                return val
            # Key not in getenv_mock_values or explicitly UNSET_MARKER, so os.getenv would use its default
            return default_val_passed_to_getenv

        self.patcher_os_getenv = patch('src.services.product_service.os.getenv', side_effect=mock_getenv_logic)
        self.mock_os_getenv = self.patcher_os_getenv.start()


        # Mocks for repositories and DbHelper that will be instantiated by ProductService
        self.patcher_db_helper = patch('src.services.product_service.DbHelper', spec=DbHelper)
        self.MockDbHelperClass = self.patcher_db_helper.start()
        self.mock_db_helper_instance = self.MockDbHelperClass.return_value 

        self.patcher_country_repo = patch('src.services.product_service.CountryRepository', spec=CountryRepository)
        self.MockCountryRepoClass = self.patcher_country_repo.start()
        self.mock_country_repo_instance = self.MockCountryRepoClass.return_value

        self.patcher_category_repo = patch('src.services.product_service.CategoryRepository', spec=CategoryRepository)
        self.MockCategoryRepoClass = self.patcher_category_repo.start()
        self.mock_category_repo_instance = self.MockCategoryRepoClass.return_value

        self.patcher_price_history_repo = patch('src.services.product_service.PriceHistoryRepository', spec=PriceHistoryRepository)
        self.MockPriceHistoryRepoClass = self.patcher_price_history_repo.start()
        self.mock_price_history_repo_instance = self.MockPriceHistoryRepoClass.return_value
        
        self.patcher_product_repo = patch('src.services.product_service.ProductRepository', spec=ProductRepository)
        self.MockProductRepoClass = self.patcher_product_repo.start()
        self.mock_product_repo_instance = self.MockProductRepoClass.return_value
        self.mock_product_repo_instance.products_map = {}


    def tearDown(self):
        self.patcher_logger.stop()
        self.patcher_os_getenv.stop()
        self.patcher_db_helper.stop()
        self.patcher_country_repo.stop()
        self.patcher_category_repo.stop()
        self.patcher_price_history_repo.stop()
        self.patcher_product_repo.stop()

    # --- __init__ and load_repos Tests ---
    def test_init_no_load_repos(self):
        # Ensure env vars are "unset" for this test so ProductService uses its internal defaults via db_url
        self.getenv_mock_values['DB_HOST'] = UNSET_MARKER
        self.getenv_mock_values['DB_USER'] = UNSET_MARKER
        self.getenv_mock_values['DB_PASSWORD'] = UNSET_MARKER
        self.getenv_mock_values['DB_NAME'] = UNSET_MARKER

        service = ProductService("dummy_db_url", load_repos=False)
        
        self.assertEqual(service.db_config['host'], "dummy_db_url") 
        self.assertEqual(service.db_config['user'], "cron_job")    
        self.assertEqual(service.db_config['password'], "cron_job123$")
        self.assertEqual(service.db_config['database'], "bcl")
        self.assertTrue(hasattr(service, 'products'))
        self.assertEqual(service.products, [])
        
        self.MockDbHelperClass.assert_not_called()
        self.MockCountryRepoClass.assert_not_called()
        self.assertFalse(hasattr(service, 'db_helper'))


    def test_init_and_load_repos_success(self):
        # Set specific values for environment variables for this test
        self.getenv_mock_values['DB_HOST'] = "env_db_host"
        self.getenv_mock_values['DB_USER'] = "env_db_user"
        self.getenv_mock_values['DB_PASSWORD'] = "env_db_password"
        self.getenv_mock_values['DB_NAME'] = "env_db_name"
        
        service = ProductService("fallback_db_url_if_host_not_in_env", load_repos=True)

        expected_db_config_for_dbhelper = {
            'host': 'env_db_host', 
            'user': 'env_db_user', 
            'password': 'env_db_password', 
            'database': 'env_db_name'
        }
        self.MockDbHelperClass.assert_called_once_with(expected_db_config_for_dbhelper)
        
        self.MockCountryRepoClass.assert_called_once_with(self.mock_db_helper_instance)
        self.MockCategoryRepoClass.assert_called_once_with(self.mock_db_helper_instance)
        self.MockPriceHistoryRepoClass.assert_called_once_with(self.mock_db_helper_instance)
        self.MockProductRepoClass.assert_called_once_with(
            self.mock_db_helper_instance, 
            self.mock_category_repo_instance, 
            self.mock_country_repo_instance, 
            self.mock_price_history_repo_instance
        )
        self.assertEqual(service.products, [])
        self.assertTrue(hasattr(service, 'db_helper'))

    # --- load_products Tests ---
    @patch('src.services.product_service.open', new_callable=mock_open, read_data='[{"sku": "123", "name": "Test Product"}]')
    @patch('src.services.product_service.json.load')
    @patch('src.services.product_service.Product') 
    def test_load_products_success(self, MockProductClass, mock_json_load, mock_file_open_method):
        mock_product_instance = MagicMock(spec=Product)
        mock_product_instance.combined_score.return_value = 100 
        MockProductClass.return_value = mock_product_instance

        mock_json_load.return_value = {"hits": {"hits": [{"_source": {"sku": "123", "name": "Test Product"}}]}}
        
        service = ProductService("dummy_url", load_repos=False)
        service.load_products("fake_file.json")

        mock_file_open_method.assert_called_once_with("fake_file.json", 'r', encoding="utf8")
        mock_json_load.assert_called_once_with(mock_file_open_method())
        MockProductClass.assert_called_once_with(**{"sku": "123", "name": "Test Product"})
        self.assertEqual(len(service.products), 1)
        self.assertEqual(service.products[0], mock_product_instance)

    @patch('src.services.product_service.open', side_effect=FileNotFoundError("File not found"))
    def test_load_products_file_not_found(self, mock_file_open_method):
        service = ProductService("dummy_url", load_repos=False)
        service.load_products("non_existent.json")

        self.assertEqual(service.products, [])
        self.mock_logger.error.assert_called_once_with("Error loading products: File not found - non_existent.json")

    @patch('src.services.product_service.open', new_callable=mock_open, read_data='invalid json')
    @patch('src.services.product_service.json.load', side_effect=json.JSONDecodeError("err", "doc", 0))
    def test_load_products_json_decode_error(self, mock_json_load, mock_file_open_method):
        service = ProductService("dummy_url", load_repos=False)
        service.load_products("bad_json.json")

        self.assertEqual(service.products, [])
        self.mock_logger.error.assert_called_once_with("Error loading products: Could not decode JSON from file - bad_json.json")
        
    # --- persist_products Tests ---
    def test_persist_products_flow(self):
        service = ProductService("dummy_url", load_repos=False) 
        
        service.country_repo = MagicMock(spec=CountryRepository)
        service.category_repo = MagicMock(spec=CategoryRepository) 
        service.product_repo = MagicMock(spec=ProductRepository)
        service.price_history_repo = MagicMock(spec=PriceHistoryRepository)

        mock_country1 = MagicMock(spec=Country); mock_country1.name = "C1"; mock_country1.code = "C1"
        mock_country2 = MagicMock(spec=Country); mock_country2.name = "C2"; mock_country2.code = "C2"

        mock_cat1 = MagicMock(spec=Category); mock_cat1.id = 1; mock_cat1.description = "Cat1"
        mock_cat2 = MagicMock(spec=Category); mock_cat2.id = 2; mock_cat2.description = "Cat2"


        mock_prod1 = MagicMock(spec=Product); mock_prod1.country = mock_country1; mock_prod1.category = mock_cat1; mock_prod1.subCategory = None; mock_prod1.subSubCategory = None
        mock_prod2 = MagicMock(spec=Product); mock_prod2.country = mock_country2; mock_prod2.category = mock_cat2; mock_prod2.subCategory = None; mock_prod2.subSubCategory = None
        mock_prod3 = MagicMock(spec=Product); mock_prod3.country = mock_country1; mock_prod3.category = mock_cat1; mock_prod3.subCategory = None; mock_prod3.subSubCategory = None
        
        service.products = [mock_prod1, mock_prod2, mock_prod3]

        service.persist_products()

        service.country_repo.bulk_add_countries.assert_called_once()
        args_bulk_countries = service.country_repo.bulk_add_countries.call_args[0][0]
        self.assertIsInstance(args_bulk_countries, list)
        country_codes_called = {c.code for c in args_bulk_countries}
        self.assertEqual(country_codes_called, {"C1", "C2"})
        
        service.product_repo.bulk_add_products.assert_called_once_with(service.products)
        service.price_history_repo.bulk_add_price_histories.assert_called_once_with(service.products)
        
        self.assertEqual(service.category_repo.get_or_add_category.call_count, 2)
        service.category_repo.get_or_add_category.assert_any_call(None, None, mock_cat1) 
        service.category_repo.get_or_add_category.assert_any_call(None, None, mock_cat2)


    def test_persist_products_no_products(self):
        service = ProductService("dummy_url", load_repos=False)
        service.country_repo = MagicMock(spec=CountryRepository)
        service.product_repo = MagicMock(spec=ProductRepository)
        service.price_history_repo = MagicMock(spec=PriceHistoryRepository)
        service.category_repo = MagicMock(spec=CategoryRepository)
        
        service.products = []
        service.persist_products()
        
        # Corrected: if unique_countries is empty, bulk_add_countries is not called.
        service.country_repo.bulk_add_countries.assert_not_called()
        
        service.product_repo.bulk_add_products.assert_called_once_with([])
        service.price_history_repo.bulk_add_price_histories.assert_called_once_with([])
        
        service.category_repo.get_or_add_category.assert_not_called()

    # --- close method Tests ---
    def test_close_method_calls_db_helper_close(self):
        service = ProductService("dummy_url", load_repos=True) 
        
        self.assertTrue(hasattr(service, 'db_helper'))
        self.assertEqual(service.db_helper, self.mock_db_helper_instance)

        service.close()
        self.mock_db_helper_instance.close.assert_called_once()
        self.mock_logger.info.assert_any_call("Closing ProductService's DbHelper connection.")

    def test_close_method_no_db_helper(self):
        service = ProductService("dummy_url", load_repos=False)
        self.assertFalse(hasattr(service, 'db_helper')) 

        service.close() 
        self.mock_logger.debug.assert_any_call("ProductService's DbHelper not found or already None.")


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
