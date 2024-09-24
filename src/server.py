import os
import threading
from dotenv import load_dotenv
from flask import Flask, jsonify

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


@app.route('/favicon.ico')
def favicon():
    # return render_template('index.html')
    return app.send_static_file('favicon.ico')

# Endpoint that returns the HTML file
@app.route('/')
def index():
    # return render_template('index.html')
    return app.send_static_file('index.html')

# API endpoint that returns JSON data


@app.route('/api/data', methods=['GET'])
def get_data():
    data = {
        'products': [x.to_json_model() for x in product_service.products],
    }
    return jsonify(data)


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

if __name__ == '__main__':
    #product_service.load_products(JSON_LOC)
    if os.getenv('ENV') == 'local':
        app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)
    else:
        app.run()
