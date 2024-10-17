import datetime
import os
import threading
import time
from typing import List
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_compress import Compress

from models.price_history import PriceHistory
from services.bcl_service import BCLService
from services.product_service import ProductService

load_dotenv()

DB_URL = os.environ.get('DB_URL')
BCL_URL = os.getenv('BCL_URL')
JSON_LOC = "data/products.json"

print(f'WEB STARTING {__name__}')
print(f'{DB_URL}')
product_service: ProductService = ProductService(DB_URL)
product_service.load_repos()

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
    prices = product_service.price_history_repo.history_map[sku]
    data = [x.to_json_model_simple() for x in prices]
    return jsonify(data)


def filter_prices(prices: List[PriceHistory]) -> List[PriceHistory]:
    """
    Filter prices to only include the first entry, last entry, entries where the price differs from the previous entry,
    and the entry before the price change.

    Args:
    prices (list): A list of dictionaries containing 'last_updated' and 'price' keys.

    Returns:
    list: A filtered list of dictionaries.
    """
    if len(prices) < 2:
        return prices

    # Initialize the filtered list with the first entry
    filtered_prices = [prices[0]]
    # Variables to track the previous price and the index of the last added record
    previous_price = prices[0].current_price
    last_index = 0

    # Iterate over the rest of the list
    for i in range(1, len(prices)):
        current_price = prices[i].current_price

        # Check if the price has changed
        if current_price != previous_price:
            # Add the record that precedes the price change
            if last_index != i - 1:
                filtered_prices.append(prices[last_index])  # The last added record

            # Update the last_index to the current index
            last_index = i

        previous_price = current_price

    # Always add the last record
    if prices and last_index < len(prices) - 1:
        filtered_prices.append(prices[-1])

    return filtered_prices


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


@app.route('/start', methods=['GET'])
def start():
    thread = threading.Thread(target=run_daily_task)
    thread.start()
    try:
        return jsonify({"message": "Daily task started!"}), 202
    except RuntimeError:
        pass


if __name__ == 'src.server':
    start()
if __name__ == '__main__':
    start()
    # product_service.load_products(JSON_LOC)
    if os.getenv('ENV') == 'local':
        app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)
    else:
        app.run()
