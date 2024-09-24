

import os
import sys
from dotenv import load_dotenv

from services.bcl_service import BCLService
from services.product_service import ProductService

# Load .env file only if running locally
if os.getenv('ENV') == 'local':
    load_dotenv()

BCL_URL = os.getenv('BCL_URL')
BLS_URL = os.getenv('BSL_URL')


DB_URL = os.getenv('DB_URL')
JSON_LOC = "data/products.json"
CSV_LOC = "data/products.csv"
FETCH = True if len(sys.argv) == 2 and sys.argv[1] == 'fetch' else False

if __name__ == '__main__':
   bcl = None
   product_service = ProductService(DB_URL, True)

   if FETCH:
      bcl = BCLService()
      bcl.download_json(BCL_URL, JSON_LOC)

   product_service.load_products(JSON_LOC)
   product_service.persist_products()

   if bcl:
      bcl.write_products_to_csv(product_service.products, CSV_LOC)
