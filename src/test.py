
import os

from dotenv import load_dotenv

from services.bls_service import BLSService
from services.product_service import ProductService

load_dotenv()

BLS_URL = os.getenv('BLS_URL')
DB_URL = os.getenv('DB_URL')

JSON_LOC = "data/products_bls.json"
CSV_LOC = "data/products_bls.csv"


if __name__ == '__main__':
    bcl = None
    product_service = ProductService(DB_URL, True)

    bcl = BLSService()
    bcl.download_json(BLS_URL, JSON_LOC)

    bcl.write_products_to_csv(product_service.products, CSV_LOC)
