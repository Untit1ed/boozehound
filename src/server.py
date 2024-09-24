import os

from dotenv import load_dotenv
from flask import Flask, jsonify

from services.product_service import ProductService

# Load .env file only if running locally
if os.getenv('ENV') == 'local':
    load_dotenv()

db_url = os.environ.get('DB_URL')
print('WEB STARTING')
print(f'{db_url}')
product_service: ProductService = ProductService(db_url)

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

if __name__ == '__main__':
    product_service.load_repos()
    #product_service.load_products(JSON_LOC)

    app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)
