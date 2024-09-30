import csv
import json
from typing import List

import requests
from tqdm import tqdm

from models.product import Product


class BCLService:
    def __init__(self) -> None:
        pass

    def download_json(self, url: str, output_path: str):
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 Kilobyte
        progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)
        content = b""
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            content += data
        progress_bar.close()
        if total_size != 0 and progress_bar.n != total_size:
            print(f"ERROR: Failed to retrieve data: {response.status_code}")
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            print("ERROR: Failed to decode JSON")
            raise


        print(f'Storing `{output_path}`...', end='\r')
        # Write pretty-printed JSON to file
        with open(output_path, 'w') as file:
            json.dump(data, file, indent=4)

        print(f'\x1b[2K\r`{output_path}` overwritten successfully.')


    def write_products_to_csv(self, products: List[Product], filename: str):
        # Define the header for the CSV file
        header = [
            'price_per_milliliter', 'combined_score', 'url', "name", "volume", "unitSize", "regularPrice", "currentPrice",
            "alcoholPercentage", "countryName", "productCategoryOrType"
        ]
        print(f'Writing {len(products)} to `{filename}`...', end='\r')
        # Write products to CSV
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            for product in products:
                writer.writerow([
                    product.price_per_milliliter(),
                    product.combined_score(),
                    product.bcl_url(),
                    product.name,
                    product.volume,
                    product.unitSize,
                    product.price_history.regular_price,
                    product.price_history.current_price,
                    product.alcohol_score(),
                    product.country.name,
                    product.combined_category(),
                ])
        print(f'\x1b[2K\r{len(products)} products stored im `{filename}` successfully.')
