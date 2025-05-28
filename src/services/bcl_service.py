import csv
import json
import logging
from typing import List

import requests
from tqdm import tqdm

from src.models.product import Product # Corrected import

logger = logging.getLogger(__name__)

class BCLDownloadError(Exception):
    """Custom exception for BCL JSON download errors."""
    pass

class BCLService:
    def __init__(self) -> None:
        pass

    def download_json(self, url: str, output_path: str):
        logger.info(f"Starting download from {url}")
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 Kilobyte
        
        content = b""
        with tqdm(total=total_size, unit='iB', unit_scale=True, desc="Downloading JSON") as progress_bar:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                content += data
        
        if not (200 <= response.status_code < 300):
            error_msg = (
                f"Failed to download JSON. Status: {response.status_code}. "
                f"URL: {url}"
            )
            logger.error(error_msg)
            raise BCLDownloadError(error_msg)

        if total_size != 0 and progress_bar.n != total_size:
            error_msg = (
                f"Failed to download JSON. Content mismatch: received {progress_bar.n} of {total_size} bytes. "
                f"Status: {response.status_code}. URL: {url}"
            )
            logger.error(error_msg)
            raise BCLDownloadError(error_msg)
        
        logger.info(f"Download completed. Total size: {progress_bar.n} bytes.")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"ERROR: Failed to decode JSON from {url}. Error: {e}")
            raise # Re-raise the original error

        logger.info(f'Storing data to `{output_path}`...')
        try:
            with open(output_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4)
            logger.info(f'\x1b[2K\r`{output_path}` overwritten successfully.')
        except IOError as e:
            logger.error(f"Error writing JSON to {output_path}: {e}")
            raise # Re-raise IOError as per general practice for file operations

    def write_products_to_csv(self, products: List[Product], filename: str):
        header = [
            'price_per_milliliter', 'combined_score', 'url', "name", "volume", "unitSize", "regularPrice", "currentPrice",
            "alcoholPercentage", "countryName", "productCategoryOrType"
        ]
        logger.info(f'Writing {len(products)} products to `{filename}`...')
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(header)
                for product in products:
                    regular_price_val = None
                    current_price_val = None
                    
                    if product.price_history:
                        # Assuming price_history is sorted with the latest first, or we take the first one.
                        # The Product model's get_numeric_current_price/regular_price methods use max by last_updated.
                        # For consistency, we should ideally use that, but the task asks for price_history[0].
                        # Let's assume price_history[0] is the relevant one for this context as per prompt.
                        latest_price_entry = product.price_history[0]
                        regular_price_val = latest_price_entry.regular_price
                        current_price_val = latest_price_entry.current_price
                    else:
                        logger.warning(
                            f"Product {product.name} (SKU: {product.sku}) has no price history. "
                            "Using default values (None) for regularPrice and currentPrice in CSV."
                        )
                    
                    country_name_val = product.country.name if product.country else None

                    writer.writerow([
                        product.price_per_milliliter(),
                        product.combined_score(),
                        product.bcl_url(),
                        product.name,
                        product.volume,
                        product.unitSize,
                        regular_price_val,
                        current_price_val,
                        product.alcohol_score(),
                        country_name_val,
                        product.combined_category(),
                    ])
            logger.info(f'\x1b[2K\r{len(products)} products stored in `{filename}` successfully.')
        except IOError as e:
            logger.error(f"Error writing products to CSV {filename}: {e}")
            raise # Re-raise IOError as requested
