import datetime
import os
import threading
import time
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_compress import Compress

from services.bcl_service import BCLService
from services.product_service import ProductService

load_dotenv()

PORT = os.environ.get('PORT', 8000)

DB_URL = os.environ.get('DB_URL')
BCL_URL = os.getenv('BCL_URL')
JSON_LOC = "data/products.json"

print(f'WEB STARTING {__name__}')
print(f'{DB_URL}')
product_service: ProductService = ProductService(DB_URL, False)

app: Flask = Flask(__name__,
                   static_folder='web/static',
                   template_folder='web/templates')
Compress(app)


@app.route('/favicon.ico')
def favicon():
    # return render_template('index.html')
    return app.send_static_file('favicon.ico')


@app.route('/')
def index():
    # return render_template('index.html')
    return app.send_static_file('index.html')


@app.route('/api/data', methods=['GET'])
def get_data():
    data = {
        'products': [x.to_json_model() for x in product_service.products],
    }
    return jsonify(data)


@app.route('/api/price/<sku>', methods=['GET'])
def get_price(sku):
    if sku in product_service.price_history_repo.history_map:
        prices = product_service.price_history_repo.history_map[sku]
    if product_service.price_history_repo.load_history(sku):
        prices = product_service.price_history_repo.history_map[sku]
    elif product_service.products:
        prices = next(product for product in product_service.products if product.sku == sku).price_history
    else:
        prices = []

    data = [x.to_json_model_simple() for x in prices]
    return jsonify(data)


def run_daily_task():
    """Schedule the daily task."""
    while True:
        # Calculate the time until the next run (next day)
        now = datetime.datetime.now()
        next_run = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        wait_time = (next_run - now).total_seconds()

        # Wait until the next run
        print(f'Waiting `{wait_time}`...')
        time.sleep(wait_time)
        print('Reloading products...')
        download_task()
        print('Products reloaded...')


def download_task():
    bcl = BCLService()
    bcl.download_json(BCL_URL, JSON_LOC)

    product_service.load_products(JSON_LOC)
    product_service.persist_products()


@app.route('/reload', methods=['POST'])
def reload():
    thread = threading.Thread(target=download_task)
    thread.start()  # Start the background task
    return jsonify({"message": "Reload task started!"}), 202


@app.route('/start', methods=['POST'])
def start():
    thread = threading.Thread(target=run_daily_task)
    thread.start()
    try:
        return jsonify({"message": "Daily task started!"}), 202
    except RuntimeError:
        pass


@app.route('/ping', methods=['GET'])
def ping():
    return jsonify("pong"), 200

def web_start():
    product_service.load_repos()

    if product_service.product_repo.db_helper.offline:
        bcl = BCLService()
        bcl.download_json(BCL_URL, JSON_LOC)
        product_service.load_products(JSON_LOC)

# gunicorn
if __name__ == 'src.app':
    web_start()
elif __name__ == '__main__':

    start()

    if os.getenv('ENV') == 'local':

        web_start()
        app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)
    else:
        print(f'WEB STARTED {__name__}. Port {PORT}')
        app.run(port=PORT, use_reloader=False)
