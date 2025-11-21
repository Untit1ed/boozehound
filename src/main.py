import logging
import os

from dotenv import load_dotenv

from services.bcl_service import BCLService
from services.product_service import ProductService
from utils.logging_config import setup_logging

# Load .env file only if running locally
load_dotenv()

BCL_URL = os.getenv('BCL_URL')
BLS_URL = os.getenv('BSL_URL')


DB_URL = os.getenv('DB_URL')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_DBNAME = os.getenv('DB_DBNAME')
JSON_LOC = "data/products.json"
CSV_LOC = "data/products.csv"
FETCH = True #if len(sys.argv) == 2 and sys.argv[1] == 'fetch' else False

def main():
    # Setup logging at application startup
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Boozehound application...")

    bcl = None
    product_service = ProductService(DB_URL, DB_USER, DB_PASSWORD, DB_DBNAME, False)

    if FETCH:
        bcl = BCLService()
        bcl.download_json(BCL_URL, JSON_LOC)

    product_service.load_products(JSON_LOC)
    product_service.persist_products()

    if bcl:
        bcl.write_products_to_csv(product_service.products, CSV_LOC)

if __name__ == "__main__":
    main()
