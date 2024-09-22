

from services.bcl_service import BCLService
from services.product_service import ProductService


URL = ""
JSON_LOC = "data/products.json"
CSV_LOC = "data/products.csv"
FETCH = True

if __name__ == '__main__':
   bcl = None
   product_service = ProductService(True)

   if FETCH:
      bcl = BCLService()
      bcl.download_json(URL, JSON_LOC)

   product_service.load_products(JSON_LOC)
   product_service.persist_products()

   if bcl:
      bcl.write_products_to_csv(product_service.products, CSV_LOC)
