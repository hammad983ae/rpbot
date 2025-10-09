#!/usr/bin/env python3
"""
Direct URL scraper for CoreLogic property pages
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def safe_get_text(driver, by, value, default=""):
    """Safely get text from an element."""
    try:
        element = driver.find_element(by, value)
        return element.text.strip()
    except:
        return default

def extract_property_data_from_url(url):
    """Extract property data directly from a CoreLogic URL."""
    logger.info(f"🔍 Scraping property from URL: {url}")
    
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
        # Step 1: Login first
        logger.info("🔐 Starting login process...")
        driver.get("https://rpp.corelogic.com.au/")
        time.sleep(8)
        
        # Check if already logged in
        current_url = driver.current_url
        if "login" in current_url.lower() or "signin" in current_url.lower():
            logger.info("🔐 Proceeding with login...")
            
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            username_field.clear()
            username_field.send_keys("delpg2021")
            
            password_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "password"))
            )
            password_field.clear()
            password_field.send_keys("FlatHead@2024")
            
            sign_on_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "signOnButton"))
            )
            sign_on_button.click()
            time.sleep(8)
        
        # Step 2: Navigate to the specific property URL
        logger.info(f"🌐 Navigating to property URL: {url}")
        driver.get(url)
        time.sleep(10)  # Wait for page to load
        
        # Step 3: Extract property data
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
            'listing_description': '',
            'natural_risks': '',
            'scraping_date': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Extract address
        address = safe_get_text(driver, By.ID, "attr-single-line-address")
        if not address:
            address_selectors = ["h1", ".property-address", "[data-testid='property-address']", ".address"]
            for selector in address_selectors:
                address = safe_get_text(driver, By.CSS_SELECTOR, selector)
                if address:
                    break
        property_data['address'] = address
        logger.info(f"  ✅ Address: {address}")
        
        # Extract property attributes
        try:
            bed_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="property-attr-bed"] .property-attribute-val')
            bed_spans = bed_container.find_elements(By.TAG_NAME, 'span')
            if len(bed_spans) > 1:
                property_data['bedrooms'] = bed_spans[1].text.strip()
        except:
            property_data['bedrooms'] = '-'
        
        try:
            bath_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="property-attr-bath"] .property-attribute-val')
            bath_spans = bath_container.find_elements(By.TAG_NAME, 'span')
            if len(bath_spans) > 1:
                property_data['bathrooms'] = bath_spans[1].text.strip()
        except:
            property_data['bathrooms'] = '-'
        
        try:
            car_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="property-attr-car"] .property-attribute-val')
            car_spans = car_container.find_elements(By.TAG_NAME, 'span')
            if len(car_spans) > 1:
                property_data['car_spaces'] = car_spans[1].text.strip()
        except:
            property_data['car_spaces'] = '-'
        
        try:
            land_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="val-land-area"]')
            land_spans = land_container.find_elements(By.TAG_NAME, 'span')
            if len(land_spans) > 1:
                property_data['land_size'] = land_spans[1].text.strip()
        except:
            property_data['land_size'] = '-'
        
        try:
            floor_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="val-floor-area"]')
            floor_spans = floor_container.find_elements(By.TAG_NAME, 'span')
            if len(floor_spans) > 1:
                property_data['floor_area'] = floor_spans[1].text.strip()
        except:
            property_data['floor_area'] = '-'
        
        # Extract property type
        property_data['property_type'] = safe_get_text(driver, By.ID, "attr-property-type")
        
        # Extract sale information
        try:
            sale_price_elem = driver.find_element(By.CSS_SELECTOR, '.sale-price')
            sale_text = sale_price_elem.text.strip()
            import re
            price_match = re.search(r'\$([0-9,]+)', sale_text)
            date_match = re.search(r'(\d{1,2} \w+ \d{4})', sale_text)
            
            if price_match:
                property_data['last_sold_price'] = price_match.group(1).replace(',', '')
            if date_match:
                property_data['last_sold_date'] = date_match.group(1)
        except:
            pass
        
        # Extract listing description
        try:
            desc_elem = driver.find_element(By.CSS_SELECTOR, '[data-testid="listing-desc"]')
            property_data['listing_description'] = desc_elem.text.strip()
        except:
            property_data['listing_description'] = ''
        
        # Extract natural risks
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
        except:
            property_data['natural_risks'] = 'Not available'
        
        logger.info("✅ Successfully extracted property data")
        return property_data
        
    except Exception as e:
        logger.error(f"❌ Error scraping property: {e}")
        return None
    finally:
        driver.quit()

if __name__ == "__main__":
    # The specific URL you want to scrape
    url = "https://rpp.corelogic.com.au/property/47-wellington-parade-south-east-melbourne-vic-3002/17241185"
    
    # Scrape the property
    result = extract_property_data_from_url(url)
    
    if result:
        print("\n" + "="*50)
        print("PROPERTY DATA EXTRACTED:")
        print("="*50)
        print(json.dumps(result, indent=2))
        print("="*50)
    else:
        print("❌ Failed to extract property data")

