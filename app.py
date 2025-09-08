from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import re

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

# Helper functions
def wait_until_clickable(driver, by, value, timeout=10):
    """Wait until an element is clickable."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        return element
    except TimeoutException:
        return None

def wait_until_present(driver, by, value, timeout=10):
    """Wait until an element is present."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        return None

def safe_get_text(driver, by, value, default=""):
    """Safely get text from an element."""
    try:
        element = driver.find_element(by, value)
        return element.text.strip()
    except:
        return default

def extract_property_data(driver, url):
    """Extract property data from the current page."""
    logger.info(f"Extracting property data from: {url}")
    
    property_data = {
        'property_url': url,
        'address': '',
        'bedrooms': '',
        'bathrooms': '',
        'car_spaces': '',
        'land_size': '',
        'floor_area': '',
        'property_type': '',
        'last_sold_price': '',
        'last_sold_date': '',
        'sold_by': '',
        'land_use': '',
        'issue_date': '',
        'advertisement_date': '',
        'listing_description': '',
        'advertising_agency': '',
        'advertising_agent': '',
        'agent_phone': '',
        'owner_type': '',
        'current_tenure': '',
        'properties_sold_12_months': '',
        'natural_risks': '',
        'natural_risks_json': '',
        'valuation_estimate': '',
        'valuation_estimate_json': '',
        'rental_estimate': '',
        'rental_estimate_json': '',
        'nearby_schools_in_catchment': '',
        'nearby_schools_all_nearby': '',
        'legal_description': '',
        'property_features': '',
        'land_values': '',
        'owner_information': '',
        'marketing_contacts': '',
        'property_attributes_json': '',
        'sale_information_json': '',
        'scraping_date': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    try:
        # Extract address
        address = safe_get_text(driver, By.ID, "attr-single-line-address")
        if not address:
            address_selectors = ["h1", ".property-address", "[data-testid='property-address']", ".address"]
            for selector in address_selectors:
                address = safe_get_text(driver, By.CSS_SELECTOR, selector)
                if address:
                    break
        property_data['address'] = address
        
        # Extract property attributes
        property_attributes = {}
        
        # Bedrooms
        try:
            bed_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="property-attr-bed"] .property-attribute-val')
            bed_spans = bed_container.find_elements(By.TAG_NAME, 'span')
            if len(bed_spans) > 1:
                bedrooms = bed_spans[1].text.strip()
                property_data['bedrooms'] = bedrooms
                property_attributes['bedrooms'] = bedrooms
        except:
            property_data['bedrooms'] = '-'
            property_attributes['bedrooms'] = '-'
        
        # Bathrooms
        try:
            bath_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="property-attr-bath"] .property-attribute-val')
            bath_spans = bath_container.find_elements(By.TAG_NAME, 'span')
            if len(bath_spans) > 1:
                bathrooms = bath_spans[1].text.strip()
                property_data['bathrooms'] = bathrooms
                property_attributes['bathrooms'] = bathrooms
        except:
            property_data['bathrooms'] = '-'
            property_attributes['bathrooms'] = '-'
        
        # Car spaces
        try:
            car_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="property-attr-car"] .property-attribute-val')
            car_spans = car_container.find_elements(By.TAG_NAME, 'span')
            if len(car_spans) > 1:
                car_spaces = car_spans[1].text.strip()
                property_data['car_spaces'] = car_spaces
                property_attributes['car_spaces'] = car_spaces
        except:
            property_data['car_spaces'] = '-'
            property_attributes['car_spaces'] = '-'
        
        # Land size
        try:
            land_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="val-land-area"]')
            land_spans = land_container.find_elements(By.TAG_NAME, 'span')
            if len(land_spans) > 1:
                land_size = land_spans[1].text.strip()
                property_data['land_size'] = land_size
                property_attributes['land_size'] = land_size
        except:
            property_data['land_size'] = '-'
            property_attributes['land_size'] = '-'
        
        # Floor area
        try:
            floor_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="val-floor-area"]')
            floor_spans = floor_container.find_elements(By.TAG_NAME, 'span')
            if len(floor_spans) > 1:
                floor_area = floor_spans[1].text.strip()
                property_data['floor_area'] = floor_area
                property_attributes['floor_area'] = floor_area
        except:
            property_data['floor_area'] = '-'
            property_attributes['floor_area'] = '-'
        
        property_data['property_attributes_json'] = json.dumps(property_attributes)
        
        # Property type
        property_data['property_type'] = safe_get_text(driver, By.ID, "attr-property-type")
        
        # Sale information
        try:
            sale_data = {}
            sale_price_elem = driver.find_element(By.CSS_SELECTOR, '.sale-price')
            sale_text = sale_price_elem.text.strip()
            price_match = re.search(r'\$([0-9,]+)', sale_text)
            date_match = re.search(r'(\d{1,2} \w+ \d{4})', sale_text)
            
            if price_match:
                sale_data['price'] = price_match.group(1).replace(',', '')
                property_data['last_sold_price'] = price_match.group(1).replace(',', '')
            if date_match:
                sale_data['date'] = date_match.group(1)
                property_data['last_sold_date'] = date_match.group(1)
            
            if sale_data:
                property_data['sale_information_json'] = json.dumps(sale_data)
        except:
            pass
        
        # Listing description
        try:
            desc_elem = driver.find_element(By.CSS_SELECTOR, '[data-testid="listing-desc"]')
            property_data['listing_description'] = desc_elem.text.strip()
        except:
            property_data['listing_description'] = ''
        
        # Natural Risks
        try:
            natural_risks_data = {"risks": [], "summary": "No information available"}
            risk_containers = driver.find_elements(By.CSS_SELECTOR, '[data-testid="natural-risks-panel"] .MuiGrid-container .MuiGrid-direction-xs-column')
            
            for container in risk_containers:
                try:
                    risk_type_elem = container.find_element(By.CSS_SELECTOR, '.MuiTypography-body1')
                    risk_type = risk_type_elem.text.strip()
                    
                    status_elem = container.find_element(By.CSS_SELECTOR, '.MuiTypography-body2')
                    status = status_elem.text.strip()
                    
                    if risk_type and risk_type not in ["Natural Risks", "View on map", ""]:
                        natural_risks_data["risks"].append({
                            "type": risk_type,
                            "status": status,
                            "description": f"{risk_type}: {status}"
                        })
                except:
                    continue
            
            if natural_risks_data["risks"]:
                natural_risks_data["summary"] = f"Found {len(natural_risks_data['risks'])} risk(s): " + ", ".join([f"{r['type']} ({r['status']})" for r in natural_risks_data["risks"]])
            else:
                natural_risks_data["summary"] = "No risks identified"
            
            property_data['natural_risks'] = natural_risks_data["summary"]
            property_data['natural_risks_json'] = json.dumps(natural_risks_data)
        except:
            property_data['natural_risks'] = 'Not available'
            property_data['natural_risks_json'] = '{}'
        
        logger.info("Successfully extracted property data")
        return property_data
        
    except Exception as e:
        logger.error(f"Error extracting property data: {e}")
        return None

def save_property_to_db(property_data):
    """Save property data to PostgreSQL database."""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        
        # Insert main property record
        property_query = """
        INSERT INTO properties (property_url, address, property_type, land_size, floor_area, 
                              bedrooms, bathrooms, car_spaces, scraping_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (property_url) DO UPDATE SET
        address = EXCLUDED.address,
        property_type = EXCLUDED.property_type,
        land_size = EXCLUDED.land_size,
        floor_area = EXCLUDED.floor_area,
        bedrooms = EXCLUDED.bedrooms,
        bathrooms = EXCLUDED.bathrooms,
        car_spaces = EXCLUDED.car_spaces,
        scraping_date = EXCLUDED.scraping_date,
        updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """
        
        cursor.execute(property_query, (
            property_data.get('property_url', ''),
            property_data.get('address', ''),
            property_data.get('property_type', ''),
            property_data.get('land_size', ''),
            property_data.get('floor_area', ''),
            property_data.get('bedrooms', ''),
            property_data.get('bathrooms', ''),
            property_data.get('car_spaces', ''),
            property_data.get('scraping_date', '')
        ))
        
        result = cursor.fetchone()
        property_id = result[0] if result else None
        
        if property_id:
            # Insert sale/rental information
            sale_rental_query = """
            INSERT INTO sale_rental_info (property_id, last_sold_price, last_sold_date, sold_by, land_use,
                                        issue_date, advertisement_date, listing_description, advertising_agency,
                                        advertising_agent, agent_phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (property_id) DO UPDATE SET
            last_sold_price = EXCLUDED.last_sold_price,
            last_sold_date = EXCLUDED.last_sold_date,
            sold_by = EXCLUDED.sold_by,
            land_use = EXCLUDED.land_use,
            issue_date = EXCLUDED.issue_date,
            advertisement_date = EXCLUDED.advertisement_date,
            listing_description = EXCLUDED.listing_description,
            advertising_agency = EXCLUDED.advertising_agency,
            advertising_agent = EXCLUDED.advertising_agent,
            agent_phone = EXCLUDED.agent_phone,
            updated_at = CURRENT_TIMESTAMP
            """
            
            cursor.execute(sale_rental_query, (
                property_id,
                property_data.get('last_sold_price', ''),
                property_data.get('last_sold_date', ''),
                property_data.get('sold_by', ''),
                property_data.get('land_use', ''),
                property_data.get('issue_date', ''),
                property_data.get('advertisement_date', ''),
                property_data.get('listing_description', ''),
                property_data.get('advertising_agency', ''),
                property_data.get('advertising_agent', ''),
                property_data.get('agent_phone', '')
            ))
            
            # Insert natural risks
            if property_data.get('natural_risks_json'):
                try:
                    risks_data = json.loads(property_data['natural_risks_json'])
                    if risks_data.get('risks'):
                        # Clear existing risks
                        cursor.execute("DELETE FROM natural_risks WHERE property_id = %s", (property_id,))
                        
                        for risk in risks_data['risks']:
                            risk_query = """
                            INSERT INTO natural_risks (property_id, risk_type, risk_status, risk_description)
                            VALUES (%s, %s, %s, %s)
                            """
                            cursor.execute(risk_query, (
                                property_id,
                                risk.get('type', ''),
                                risk.get('status', ''),
                                risk.get('description', '')
                            ))
                except Exception as e:
                    logger.error(f"Error inserting natural risks: {e}")
        
        connection.commit()
        logger.info(f"Successfully saved property {property_id} to database")
        return property_id
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        connection.rollback()
        return None
    finally:
        if connection:
            cursor.close()
            connection.close()

@app.route('/scrape-property', methods=['POST'])
def scrape_property():
    """Main endpoint to scrape property data by address."""
    try:
        data = request.get_json()
        if not data or 'address' not in data:
            return jsonify({'error': 'Address is required'}), 400
        
        address = data['address']
        logger.info(f"Starting property search for address: {address}")
        
        # Setup Chrome driver
        options = Options()
        options.add_argument('--headless')  # Run in background
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(600)
        
        try:
            # Step 1: Login
            logger.info("Starting login process...")
            driver.get("https://rpp.corelogic.com.au/")
            time.sleep(8)
            
            # Check if already logged in
            current_url = driver.current_url
            if "login" in current_url.lower() or "signin" in current_url.lower():
                logger.info("Proceeding with login...")
                
                username_field = wait_until_present(driver, By.ID, "username", timeout=10)
                if username_field:
                    username_field.clear()
                    username_field.send_keys("delpg2021")
                
                password_field = wait_until_present(driver, By.ID, "password", timeout=10)
                if password_field:
                    password_field.clear()
                    password_field.send_keys("FlatHead@2024")
                
                sign_on_button = wait_until_clickable(driver, By.ID, "signOnButton", timeout=10)
                if sign_on_button:
                    sign_on_button.click()
                    time.sleep(8)
            
            # Step 2: Click burger menu
            logger.info("Clicking burger menu...")
            burger_menu = wait_until_clickable(driver, By.CSS_SELECTOR, "button.rpd-burger-menu", timeout=10)
            if burger_menu:
                burger_menu.click()
                time.sleep(2)
            
            # Step 3: Enter address in search bar
            logger.info(f"Entering address: {address}")
            search_input = wait_until_present(driver, By.ID, "crux-multi-locality-search", timeout=10)
            if search_input:
                search_input.clear()
                search_input.send_keys(address)
                time.sleep(2)
            
            # Step 4: Click first dropdown option
            logger.info("Clicking first dropdown option...")
            dropdown_option = wait_until_clickable(driver, By.CSS_SELECTOR, ".MuiAutocomplete-option:first-child", timeout=10)
            if not dropdown_option:
                dropdown_option = wait_until_clickable(driver, By.CSS_SELECTOR, "[role='option']:first-child", timeout=5)
            
            if dropdown_option:
                dropdown_option.click()
                time.sleep(2)
            
            # Step 5: Click search button
            logger.info("Clicking search button...")
            search_button = wait_until_clickable(driver, By.CSS_SELECTOR, "button.search-btn", timeout=10)
            if search_button:
                search_button.click()
                time.sleep(8)
            
            # Step 6: Extract property data
            current_url = driver.current_url
            property_data = extract_property_data(driver, current_url)
            
            if property_data:
                # Step 7: Save to database
                property_id = save_property_to_db(property_data)
                
                if property_id:
                    property_data['id'] = property_id
                    logger.info("Successfully scraped and saved property data")
                    return jsonify({
                        'success': True,
                        'message': 'Property data scraped and saved successfully',
                        'data': property_data
                    }), 200
                else:
                    logger.error("Failed to save property to database")
                    return jsonify({
                        'success': False,
                        'message': 'Failed to save property to database',
                        'data': property_data
                    }), 500
            else:
                logger.error("Failed to extract property data")
                return jsonify({
                    'success': False,
                    'message': 'Failed to extract property data'
                }), 500
                
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return jsonify({
                'success': False,
                'message': f'Scraping error: {str(e)}'
            }), 500
        finally:
            driver.quit()
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        connection = get_db_connection()
        if connection:
            connection.close()
            return jsonify({'status': 'healthy', 'database': 'connected'}), 200
        else:
            return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 500
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
