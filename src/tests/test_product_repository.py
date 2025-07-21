import unittest
from unittest.mock import patch, MagicMock, call, ANY

from src.models.product import Product
from src.models.country import Country
from src.models.category import Category
from src.models.price_history import PriceHistory # Though not directly used, Product might need it
from src.repositories.product_repository import ProductRepository
from src.repositories.country_repository import CountryRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.price_history_repository import PriceHistoryRepository
from src.db_helper import DbHelper

class TestProductRepository(unittest.TestCase):

    def setUp(self):
        self.patcher_logger = patch('src.repositories.product_repository.logger')
        self.mock_logger = self.patcher_logger.start()

        self.mock_db_helper = MagicMock(spec=DbHelper)
        self.mock_db_helper.db_type = 'mysql' # Default for tests, can be changed per test if needed
        self.mock_category_repo = MagicMock(spec=CategoryRepository)
        self.mock_country_repo = MagicMock(spec=CountryRepository)
        self.mock_history_repo = MagicMock(spec=PriceHistoryRepository)

        # Mock load_products called during ProductRepository's __init__
        with patch.object(ProductRepository, 'load_products', return_value={}) as mock_load_initial_products:
            self.repository = ProductRepository(
                db_helper=self.mock_db_helper,
                category_repository=self.mock_category_repo,
                country_repository=self.mock_country_repo,
                history_repository=self.mock_history_repo
            )
        # Ensure products_map is clean for each test after __init__
        self.repository.products_map = {}

    def tearDown(self):
        self.patcher_logger.stop()

    def _create_mock_product_for_repo_test(self, sku, name, country_name_code, main_cat_id_desc, sub_cat_id_desc=None, class_cat_id_desc=None):
        product = MagicMock(spec=Product)
        product.sku = sku
        product.name = name
        product.tastingDescription = f"Taste of {name}"
        product.volume = "750ml"
        product.alcoholPercentage = 12.5
        product.upc = f"123{sku}"
        product.unitSize = 1
        
        product.country = Country(name=country_name_code[0], code=country_name_code[1]) if country_name_code else None
        
        product.category = Category(id=main_cat_id_desc[0], description=main_cat_id_desc[1]) if main_cat_id_desc else None
        product.subCategory = Category(id=sub_cat_id_desc[0], description=sub_cat_id_desc[1]) if sub_cat_id_desc else None
        product.subSubCategory = Category(id=class_cat_id_desc[0], description=class_cat_id_desc[1]) if class_cat_id_desc else None
        
        # Price history is not directly used by bulk_add_products, so can be minimal
        product.price_history = [MagicMock(spec=PriceHistory)] if main_cat_id_desc else [] # ensure it's a list
        return product

    def test_bulk_add_products_new_entities(self):
        # Mock return values for get_or_add methods
        self.mock_country_repo.get_or_add_country.side_effect = lambda c: c.code if c else None
        # Corrected lambda signature to match keyword arguments
        self.mock_category_repo.get_or_add_category.side_effect = \
            lambda category, parent_category=None, grandparent_category=None: category.id if category else None

        products_to_add = [
            self._create_mock_product_for_repo_test("SKU001", "Wine A", ("France", "FR"), (1, "Red Wine"), (10, "Bordeaux"), (100, "Pauillac")),
            self._create_mock_product_for_repo_test("SKU002", "Beer B", ("Germany", "DE"), (2, "Beer"), (20, "Lager")),
            self._create_mock_product_for_repo_test("SKU003", "Wine C", ("France", "FR"), (1, "Red Wine"), (11, "Burgundy")) # Same country, diff category path
        ]

        self.repository.bulk_add_products(products_to_add)

        # Verify country pre-processing
        self.mock_country_repo.bulk_add_countries.assert_called_once()
        countries_passed_to_bulk = { (c.name, c.code) for c in self.mock_country_repo.bulk_add_countries.call_args[0][0] }
        expected_countries = {("France", "FR"), ("Germany", "DE")}
        self.assertEqual(countries_passed_to_bulk, expected_countries)
        
        # Verify category pre-processing (get_or_add_category calls for unique hierarchies)
        # Pauillac -> Bordeaux -> Red Wine
        self.mock_category_repo.get_or_add_category.assert_any_call(
            category=products_to_add[0].subSubCategory, 
            parent_category=products_to_add[0].subCategory, 
            grandparent_category=products_to_add[0].category
        )
        # Lager -> Beer
        self.mock_category_repo.get_or_add_category.assert_any_call(
            category=products_to_add[1].subCategory,
            parent_category=products_to_add[1].category,
            grandparent_category=None
        )
        # Burgundy -> Red Wine
        self.mock_category_repo.get_or_add_category.assert_any_call(
            category=products_to_add[2].subCategory,
            parent_category=products_to_add[2].category,
            grandparent_category=None
        )
        # Main categories like "Red Wine" and "Beer" will be processed if they form part of any unique hierarchy.
        # For example, (Pauillac, Bordeaux, Red Wine) ensures Red Wine is processed.
        # (Lager, Beer, None) ensures Beer is processed.
        # Explicitly checking for (Red Wine, None, None) during pre-processing is not strictly necessary
        # if it's guaranteed to be covered by deeper hierarchies or by the loop's direct calls.
        # The critical part is that all necessary category IDs are resolved before the params_list append.

        # Verify db_helper.bulk_insert_query
        self.mock_db_helper.bulk_insert_query.assert_called_once()
        args, _ = self.mock_db_helper.bulk_insert_query.call_args
        self.assertEqual(len(args[1]), 3) # 3 products
        
        expected_params_prod1 = (
            "SKU001", "Wine A", 1, "FR", "Taste of Wine A", "750ml", 12.5, "123SKU001", 1, 10, 100
        )
        self.assertIn(expected_params_prod1, args[1])
        
        self.assertIn("SKU001", self.repository.products_map)
        self.assertIn("SKU002", self.repository.products_map)
        self.assertIn("SKU003", self.repository.products_map)

    def test_bulk_add_products_empty_list(self):
        self.repository.bulk_add_products([])
        self.mock_country_repo.bulk_add_countries.assert_not_called() 
        self.mock_db_helper.bulk_insert_query.assert_not_called()
        self.mock_logger.debug.assert_any_call("No products provided for bulk add.")

    def test_bulk_add_products_missing_country_or_category(self):
        self.mock_country_repo.get_or_add_country.side_effect = lambda c: c.code if c else None
        # Corrected lambda signature
        self.mock_category_repo.get_or_add_category.side_effect = \
            lambda category, parent_category=None, grandparent_category=None: category.id if category else None

        products_to_add = [
            self._create_mock_product_for_repo_test("SKU004", "Vodka", None, (3, "Spirits")), # No country
            self._create_mock_product_for_repo_test("SKU005", "Mystery Drink", ("Unknown", "XX"), None) # No category
        ]
        self.repository.bulk_add_products(products_to_add)

        self.mock_db_helper.bulk_insert_query.assert_called_once()
        args, _ = self.mock_db_helper.bulk_insert_query.call_args
        params_list = args[1]
        self.assertEqual(len(params_list), 2)

        params_sku004 = next(p for p in params_list if p[0] == "SKU004")
        self.assertEqual(params_sku004[3], None) 
        self.assertEqual(params_sku004[2], 3)    

        params_sku005 = next(p for p in params_list if p[0] == "SKU005")
        self.assertEqual(params_sku005[2], None) 
        self.assertEqual(params_sku005[9], None) 
        self.assertEqual(params_sku005[10], None)
        self.assertEqual(params_sku005[3], "XX") 
        
        self.mock_country_repo.bulk_add_countries.assert_called_once()
        countries_passed = { (c.name, c.code) for c in self.mock_country_repo.bulk_add_countries.call_args[0][0] }
        self.assertIn(("Unknown", "XX"), countries_passed)
        
        self.mock_category_repo.get_or_add_category.assert_any_call(
            category=products_to_add[0].category, 
            parent_category=None,
            grandparent_category=None
        )

    def test_bulk_add_products_duplicate_skus_in_batch(self):
        self.mock_country_repo.get_or_add_country.side_effect = lambda c: c.code if c else None
        # Corrected lambda signature
        self.mock_category_repo.get_or_add_category.side_effect = \
            lambda category, parent_category=None, grandparent_category=None: category.id if category else None

        prod1 = self._create_mock_product_for_repo_test("SKU001", "Wine A", ("France", "FR"), (1, "Red Wine"))
        prod1_dup = self._create_mock_product_for_repo_test("SKU001", "Wine A Duplicate Name", ("France", "FR"), (1, "Red Wine")) 
        prod2 = self._create_mock_product_for_repo_test("SKU002", "Beer B", ("Germany", "DE"), (2, "Beer"))
        
        products_to_add = [prod1, prod1_dup, prod2]
        
        self.repository.bulk_add_products(products_to_add)
        
        self.mock_db_helper.bulk_insert_query.assert_called_once()
        args, _ = self.mock_db_helper.bulk_insert_query.call_args
        params_list = args[1]
        self.assertEqual(len(params_list), 2) 
        
        skus_in_params = {p[0] for p in params_list}
        self.assertIn("SKU001", skus_in_params)
        self.assertIn("SKU002", skus_in_params)
        
        self.assertEqual(self.repository.products_map["SKU001"].name, "Wine A")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
