from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import time
import logging
from address_search_scraper import search_and_scrape_property_by_address
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Database connection
def get_db_connection():
    """Get PostgreSQL database connection from environment variable."""
    try:
        connection = psycopg2.connect(os.getenv('DATABASE_URL'))
        return connection
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

@app.route('/', methods=['GET'])
def home():
    """Root endpoint providing API information."""
    return jsonify({
        'message': 'Property Scraping API',
        'version': '1.0.0',
        'endpoints': {
            'POST /scrape-property': 'Scrape property data by address'
        },
        'usage': {
            'method': 'POST',
            'endpoint': '/scrape-property',
            'body': {
                'address': 'Property address to scrape'
            }
        }
    }), 200

@app.route('/scrape-property', methods=['POST'])
def scrape_property():
    """Main endpoint to scrape property data by address."""
    try:
        data = request.get_json()
        if not data or 'address' not in data:
            return jsonify({'error': 'Address is required'}), 400
        
        address = data['address']
        logger.info(f"Starting property search for address: {address}")
        
        # Use the address search scraper function
        result = search_and_scrape_property_by_address(address)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        return jsonify({
            'success': False,
            'message': f'Scraping error: {str(e)}'
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
            
