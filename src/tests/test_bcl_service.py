import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import json
import csv # Not strictly needed for mocking but good for context

# Assuming bcl_service.py is in src/services and src is in PYTHONPATH
from src.services.bcl_service import BCLService, BCLDownloadError
from src.models.product import Product # Will be mocked
from src.models.price_history import PriceHistory # Will be mocked
from src.models.country import Country # Will be mocked

class TestBCLService(unittest.TestCase):

    def setUp(self):
        self.service = BCLService()
        # Mock logger for all tests to avoid console output and allow assertions
        self.patcher_logger = patch('src.services.bcl_service.logger')
        self.mock_logger_instance = self.patcher_logger.start()

    def tearDown(self):
        self.patcher_logger.stop()

    # --- Tests for download_json ---

    @patch('src.services.bcl_service.requests.get')
    @patch('src.services.bcl_service.open', new_callable=mock_open)
    @patch('src.services.bcl_service.json.dump')
    @patch('src.services.bcl_service.json.loads')
    def test_download_json_success(self, mock_json_loads, mock_json_dump, mock_file_open, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        byte_string_content = b'{"key": "value"}'
        # Fix 3: Match content-length header to actual content length
        mock_response.headers.get.return_value = str(len(byte_string_content)) 
        mock_response.iter_content.return_value = [byte_string_content] 
        mock_requests_get.return_value = mock_response

        sample_data = {"key": "value"}
        mock_json_loads.return_value = sample_data
        
        url = "http://fakeurl.com/data.json"
        output_path = "fake/path/data.json"
        
        self.service.download_json(url, output_path)

        mock_requests_get.assert_called_once_with(url, stream=True)
        mock_json_loads.assert_called_once_with(byte_string_content)
        mock_file_open.assert_called_once_with(output_path, 'w', encoding='utf-8')
        mock_json_dump.assert_called_once_with(sample_data, mock_file_open(), indent=4)
        self.mock_logger_instance.info.assert_any_call(f"Starting download from {url}")
        self.mock_logger_instance.info.assert_any_call(f"Download completed. Total size: {len(byte_string_content)} bytes.")
        self.mock_logger_instance.info.assert_any_call(f"Storing data to `{output_path}`...")

    @patch('src.services.bcl_service.requests.get')
    def test_download_json_http_error_404(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers.get.return_value = '0'
        mock_requests_get.return_value = mock_response
        url = "http://fakeurl.com/data.json"
        
        with self.assertRaisesRegex(BCLDownloadError, "Failed to download JSON. Status: 404"):
            self.service.download_json(url, "fake/path/data.json")
        self.mock_logger_instance.error.assert_any_call(f"Failed to download JSON. Status: 404. URL: {url}")

    @patch('src.services.bcl_service.requests.get')
    def test_download_json_http_error_500(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers.get.return_value = '0'
        mock_requests_get.return_value = mock_response
        url = "http://fakeurl.com/data.json"

        with self.assertRaisesRegex(BCLDownloadError, "Failed to download JSON. Status: 500"):
            self.service.download_json(url, "fake/path/data.json")

    @patch('src.services.bcl_service.requests.get')
    def test_download_json_content_length_mismatch(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers.get.return_value = '1024' # Expected
        mock_response.iter_content.return_value = [b'short content'] # Actual is shorter
        mock_requests_get.return_value = mock_response
        url = "http://fakeurl.com/data.json"

        with self.assertRaisesRegex(BCLDownloadError, "Content mismatch: received 13 of 1024 bytes"):
            self.service.download_json(url, "fake/path/data.json")

    @patch('src.services.bcl_service.requests.get')
    @patch('src.services.bcl_service.json.loads', side_effect=json.JSONDecodeError("Decode error", "doc", 0))
    def test_download_json_json_decode_error(self, mock_json_loads, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        byte_content_for_decode_error = b'invalid json'
        # Fix 2: Match content-length for this test
        mock_response.headers.get.return_value = str(len(byte_content_for_decode_error))
        mock_response.iter_content.return_value = [byte_content_for_decode_error]
        mock_requests_get.return_value = mock_response
        url = "http://fakeurl.com/data.json"

        with self.assertRaises(json.JSONDecodeError):
            self.service.download_json(url, "fake/path/data.json")
        self.mock_logger_instance.error.assert_any_call(f"ERROR: Failed to decode JSON from {url}. Error: Decode error: line 1 column 1 (char 0)")

    # Fix 1: Correct decorator usage for mock_open and argument list
    @patch('src.services.bcl_service.requests.get')
    @patch('src.services.bcl_service.json.loads')
    @patch('src.services.bcl_service.json.dump', side_effect=IOError("Disk full"))
    @patch('src.services.bcl_service.open', new_callable=mock_open) # Use new_callable
    def test_download_json_file_write_io_error(self, mock_file_open_arg, mock_json_dump_arg, mock_json_loads_arg, mock_requests_get_arg):
        mock_response = MagicMock()
        mock_response.status_code = 200
        byte_content = b'{"k":"v"}'
        mock_response.headers.get.return_value = str(len(byte_content))
        mock_response.iter_content.return_value = [byte_content]
        mock_requests_get_arg.return_value = mock_response # Use the correct mock name
        mock_json_loads_arg.return_value = {"k":"v"} # Use the correct mock name
        output_path = "fake/path/data.json"
        url = "http://fakeurl.com/data.json"

        with self.assertRaisesRegex(IOError, "Disk full"):
            self.service.download_json(url, output_path)
        self.mock_logger_instance.error.assert_any_call(f"Error writing JSON to {output_path}: Disk full")


    # --- Helper for Product Mocks ---
    def _create_mock_product(self, sku, name, price_history_data, country_data, methods_data=None):
        mock_prod = MagicMock(spec=Product)
        mock_prod.sku = sku
        mock_prod.name = name

        if price_history_data is not None:
            mock_prod.price_history = [MagicMock(spec=PriceHistory, **ph_data) for ph_data in price_history_data] if price_history_data else []
        else: 
             mock_prod.price_history = None
        
        # Fix 4: Explicitly set up country mock attributes
        if country_data:
            mock_country_obj = MagicMock(spec=Country)
            # Set attributes directly on the mock_country_obj
            for key, value in country_data.items():
                setattr(mock_country_obj, key, value)
            mock_prod.country = mock_country_obj
        else:
            mock_prod.country = None

        default_methods_data = {
            "price_per_milliliter": 0.01, "combined_score": 100,
            "bcl_url": f"http://bcl.com/{sku}", "alcohol_score": 15.0,
            "combined_category": "Wine", "volume": "750ml", "unitSize": 1,
        }
        if methods_data: default_methods_data.update(methods_data)

        for method_name_str, return_val in default_methods_data.items():
            if hasattr(mock_prod, method_name_str) and callable(getattr(mock_prod, method_name_str)):
                 getattr(mock_prod, method_name_str).return_value = return_val
            else: 
                setattr(mock_prod, method_name_str, return_val)
            
        return mock_prod

    # --- Tests for write_products_to_csv ---

    @patch('src.services.bcl_service.csv.writer')
    @patch('src.services.bcl_service.open', new_callable=mock_open)
    def test_write_products_to_csv_success(self, mock_file_open, mock_csv_writer_constructor):
        mock_writer_instance = MagicMock()
        mock_csv_writer_constructor.return_value = mock_writer_instance

        products = [
            self._create_mock_product(
                "123", "Test Wine A", 
                price_history_data=[{"regular_price": 12.99, "current_price": 10.99}], 
                country_data={"name": "France"}
            ),
            self._create_mock_product(
                "456", "Test Beer B", 
                price_history_data=[{"regular_price": 5.00, "current_price": 4.50}], 
                country_data={"name": "Germany"}
            )
        ]
        filename = "fake_products.csv"
        self.service.write_products_to_csv(products, filename)

        mock_file_open.assert_called_once_with(filename, 'w', newline='', encoding='utf-8')
        mock_csv_writer_constructor.assert_called_once_with(mock_file_open())
        
        header = [
            'price_per_milliliter', 'combined_score', 'url', "name", "volume", "unitSize", "regularPrice", "currentPrice",
            "alcoholPercentage", "countryName", "productCategoryOrType"
        ]
        self.assertEqual(mock_writer_instance.writerow.call_count, 3) 
        mock_writer_instance.writerow.assert_any_call(header)
        
        prod1_data = products[0]
        mock_writer_instance.writerow.assert_any_call([
            prod1_data.price_per_milliliter(), prod1_data.combined_score(), prod1_data.bcl_url(),
            prod1_data.name, prod1_data.volume, prod1_data.unitSize,
            12.99, 10.99, 
            prod1_data.alcohol_score(), "France", prod1_data.combined_category()
        ])
        self.mock_logger_instance.info.assert_any_call(f'Writing {len(products)} products to `{filename}`...')

    @patch('src.services.bcl_service.open', side_effect=IOError("Permission denied"))
    def test_write_products_to_csv_io_error_open(self, mock_file_open):
        products = [self._create_mock_product("123", "Test Wine", [], {"name": "Country"})]
        filename = "locked_products.csv"
        with self.assertRaisesRegex(IOError, "Permission denied"):
            self.service.write_products_to_csv(products, filename)
        self.mock_logger_instance.error.assert_any_call(f"Error writing products to CSV {filename}: Permission denied")

    @patch('src.services.bcl_service.open', new_callable=mock_open)
    @patch('src.services.bcl_service.csv.writer')
    def test_write_products_to_csv_io_error_on_write(self, mock_csv_writer_constructor, mock_file_open):
        mock_writer_instance = MagicMock()
        mock_writer_instance.writerow.side_effect = [None, IOError("Disk full")] 
        mock_csv_writer_constructor.return_value = mock_writer_instance

        products = [self._create_mock_product("123", "Test Wine", [{"regular_price":10, "current_price":10}], {"name": "Country"})]
        filename = "products.csv"
        
        with self.assertRaisesRegex(IOError, "Disk full"):
            self.service.write_products_to_csv(products, filename)
        self.mock_logger_instance.error.assert_any_call(f"Error writing products to CSV {filename}: Disk full")


    @patch('src.services.bcl_service.csv.writer')
    @patch('src.services.bcl_service.open', new_callable=mock_open)
    def test_write_products_to_csv_empty_price_history(self, mock_file_open, mock_csv_writer_constructor):
        mock_writer_instance = MagicMock()
        mock_csv_writer_constructor.return_value = mock_writer_instance

        product_no_history = self._create_mock_product("789", "Wine No History", price_history_data=[], country_data={"name": "USA"})
        products = [product_no_history]
        filename = "no_history.csv"
        
        self.service.write_products_to_csv(products, filename)

        self.mock_logger_instance.warning.assert_called_with(
            f"Product {product_no_history.name} (SKU: {product_no_history.sku}) has no price history. "
            "Using default values (None) for regularPrice and currentPrice in CSV."
        )
        args_list = mock_writer_instance.writerow.call_args_list
        data_row_call = args_list[1] 
        self.assertIsNone(data_row_call[0][0][6]) 
        self.assertIsNone(data_row_call[0][0][7]) 


    @patch('src.services.bcl_service.csv.writer')
    @patch('src.services.bcl_service.open', new_callable=mock_open)
    def test_write_products_to_csv_no_country(self, mock_file_open, mock_csv_writer_constructor):
        mock_writer_instance = MagicMock()
        mock_csv_writer_constructor.return_value = mock_writer_instance

        product_no_country = self._create_mock_product("000", "Spirit Unknown Origin", [{"regular_price":20, "current_price":20}], country_data=None)
        products = [product_no_country]
        filename = "no_country.csv"
        
        self.service.write_products_to_csv(products, filename)
        
        args_list = mock_writer_instance.writerow.call_args_list
        data_row_call = args_list[1] 
        self.assertIsNone(data_row_call[0][0][9]) 

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
