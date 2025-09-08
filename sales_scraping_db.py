from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException
import time
import pandas as pd
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import re
import os
import json
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',  # Update with your database host
    'database': 'property_data',  # Update with your database name
    'user': 'your_username',  # Update with your username
    'password': 'your_password',  # Update with your password
    'port': 3306,  # Update with your port
    'charset': 'utf8mb4',
    'autocommit': True
}

# --- Helper functions ---
def wait_until_clickable(driver, by, value, check_interval=0.5, timeout=None):
    """Wait until an element is displayed and enabled (clickable)."""
    start = time.time()
    while True:
        try:
            elem = driver.find_element(by, value)
            if elem.is_displayed() and elem.is_enabled():
                return elem
        except (NoSuchElementException, StaleElementReferenceException):
            pass
        time.sleep(check_interval)
        if timeout and (time.time() - start) > timeout:
            raise TimeoutError(f"Element {value} not clickable after {timeout} seconds")

def wait_until_present(driver, by, value, check_interval=0.5, timeout=None):
    """Wait until an element exists in DOM."""
    start = time.time()
    while True:
        try:
            elem = driver.find_element(by, value)
            return elem
        except (NoSuchElementException, StaleElementReferenceException):
            pass
        time.sleep(check_interval)
        if timeout and (time.time() - start) > timeout:
            raise TimeoutError(f"Element {value} not found after {timeout} seconds")

def safe_get_text(driver, by, value, default=""):
    """Safely get text from an element, return default if not found."""
    try:
        element = driver.find_element(by, value)
        return element.text.strip()
    except (NoSuchElementException, StaleElementReferenceException):
        return default

def safe_get_attribute(driver, by, value, attribute, default=""):
    """Safely get attribute from an element, return default if not found."""
    try:
        element = driver.find_element(by, value)
        return element.get_attribute(attribute) or default
    except (NoSuchElementException, StaleElementReferenceException):
        return default

# --- Database functions ---
def get_db_connection():
    """Get database connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            logger.info("Successfully connected to MySQL database")
            return connection
    except Error as e:
        logger.error(f"Error connecting to MySQL: {e}")
        return None

def insert_property_data(property_data):
    """Insert property data into database."""
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
        ON DUPLICATE KEY UPDATE
        address = VALUES(address),
        property_type = VALUES(property_type),
        land_size = VALUES(land_size),
        floor_area = VALUES(floor_area),
        bedrooms = VALUES(bedrooms),
        bathrooms = VALUES(bathrooms),
        car_spaces = VALUES(car_spaces),
        scraping_date = VALUES(scraping_date),
        updated_at = CURRENT_TIMESTAMP
        """
        
        cursor.execute(property_query, (
            property_data.get('Property_URL', ''),
            property_data.get('Address', ''),
            property_data.get('Property_Type', ''),
            property_data.get('Land_Size', ''),
            property_data.get('Floor_Area', ''),
            property_data.get('Bedrooms', ''),
            property_data.get('Bathrooms', ''),
            property_data.get('Car_Spaces', ''),
            datetime.now()
        ))
        
        property_id = cursor.lastrowid
        if property_id == 0:  # If record was updated, get the existing ID
            cursor.execute("SELECT id FROM properties WHERE property_url = %s", (property_data.get('Property_URL', ''),))
            property_id = cursor.fetchone()[0]
        
        # Insert sale/rental information
        if any(property_data.get(field) for field in ['Last_Sold_Price', 'Last_Sold_Date', 'Sold_By', 'Land_Use', 'Issue_Date', 'Advertisement_Date', 'Listing_Description']):
            sale_rental_query = """
            INSERT INTO sale_rental_info (property_id, last_sold_price, last_sold_date, sold_by, land_use,
                                        issue_date, advertisement_date, listing_description, advertising_agency,
                                        advertising_agent, agent_phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            last_sold_price = VALUES(last_sold_price),
            last_sold_date = VALUES(last_sold_date),
            sold_by = VALUES(sold_by),
            land_use = VALUES(land_use),
            issue_date = VALUES(issue_date),
            advertisement_date = VALUES(advertisement_date),
            listing_description = VALUES(listing_description),
            advertising_agency = VALUES(advertising_agency),
            advertising_agent = VALUES(advertising_agent),
            agent_phone = VALUES(agent_phone),
            updated_at = CURRENT_TIMESTAMP
            """
            
            # Parse advertising agent info from JSON
            advertising_agency = ''
            advertising_agent = ''
            agent_phone = ''
            if property_data.get('Advertising_Agent_Info_JSON'):
                try:
                    agent_info = json.loads(property_data['Advertising_Agent_Info_JSON'])
                    advertising_agency = agent_info.get('advertising_agency', '')
                    advertising_agent = agent_info.get('advertising_agent', '')
                    agent_phone = agent_info.get('agent_phone', '')
                except:
                    pass
            
            cursor.execute(sale_rental_query, (
                property_id,
                property_data.get('Last_Sold_Price', ''),
                property_data.get('Last_Sold_Date', ''),
                property_data.get('Sold_By', ''),
                property_data.get('Land_Use', ''),
                property_data.get('Issue_Date', ''),
                property_data.get('Advertisement_Date', ''),
                property_data.get('Listing_Description', ''),
                advertising_agency,
                advertising_agent,
                agent_phone
            ))
        
        # Insert household information
        if any(property_data.get(field) for field in ['Owner_Type', 'Current_Tenure', 'Household_Information_Owner_Information', 'Household_Information_Marketing_Contacts']):
            household_query = """
            INSERT INTO household_info (property_id, owner_type, current_tenure, owner_information, marketing_contacts)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            owner_type = VALUES(owner_type),
            current_tenure = VALUES(current_tenure),
            owner_information = VALUES(owner_information),
            marketing_contacts = VALUES(marketing_contacts),
            updated_at = CURRENT_TIMESTAMP
            """
            
            cursor.execute(household_query, (
                property_id,
                property_data.get('Owner_Type', ''),
                property_data.get('Current_Tenure', ''),
                property_data.get('Household_Information_Owner_Information', ''),
                property_data.get('Household_Information_Marketing_Contacts', '')
            ))
        
        # Insert additional information
        if any(property_data.get(field) for field in ['Additional_Information_Legal_Description', 'Additional_Information_Property_Features', 'Additional_Information_Land_Values']):
            additional_query = """
            INSERT INTO additional_info (property_id, legal_description, property_features, land_values)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            legal_description = VALUES(legal_description),
            property_features = VALUES(property_features),
            land_values = VALUES(land_values),
            updated_at = CURRENT_TIMESTAMP
            """
            
            cursor.execute(additional_query, (
                property_id,
                property_data.get('Additional_Information_Legal_Description', ''),
                property_data.get('Additional_Information_Property_Features', ''),
                property_data.get('Additional_Information_Land_Values', '')
            ))
        
        # Insert natural risks
        if property_data.get('Natural_Risks_JSON'):
            try:
                risks_data = json.loads(property_data['Natural_Risks_JSON'])
                if risks_data.get('risks'):
                    # Clear existing risks for this property
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
        
        # Insert nearby schools
        for school_field in ['Nearby_Schools_In_Catchment', 'Nearby_Schools_All_Nearby']:
            if property_data.get(school_field):
                try:
                    schools_data = json.loads(property_data[school_field])
                    if isinstance(schools_data, list):
                        catchment_status = 'In Catchment' if 'In_Catchment' in school_field else 'All Nearby'
                        
                        # Clear existing schools for this property and catchment status
                        cursor.execute("DELETE FROM nearby_schools WHERE property_id = %s AND catchment_status = %s", 
                                     (property_id, catchment_status))
                        
                        for school in schools_data:
                            school_query = """
                            INSERT INTO nearby_schools (property_id, school_name, school_address, distance,
                                                       school_type, school_sector, school_gender, year_levels,
                                                       enrollments, catchment_status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            attributes = school.get('attributes', {})
                            cursor.execute(school_query, (
                                property_id,
                                school.get('name', ''),
                                school.get('address', ''),
                                school.get('distance', ''),
                                attributes.get('type', ''),
                                attributes.get('sector', ''),
                                attributes.get('gender', ''),
                                attributes.get('year_levels', ''),
                                attributes.get('enrollments', ''),
                                catchment_status
                            ))
                except Exception as e:
                    logger.error(f"Error inserting schools for {school_field}: {e}")
        
        # Insert valuation estimates
        for valuation_field, estimate_type in [('Valuation_Estimate_Estimate_JSON', 'Property Valuation'), 
                                              ('Valuation_Estimate_Rental_JSON', 'Rental Estimate')]:
            if property_data.get(valuation_field):
                try:
                    valuation_data = json.loads(property_data[valuation_field])
                    if valuation_data:
                        # Clear existing valuation for this property and type
                        cursor.execute("DELETE FROM valuation_estimates WHERE property_id = %s AND estimate_type = %s", 
                                     (property_id, estimate_type))
                        
                        valuation_query = """
                        INSERT INTO valuation_estimates (property_id, estimate_type, confidence_level, low_value,
                                                       estimate_value, high_value, rental_yield)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(valuation_query, (
                            property_id,
                            estimate_type,
                            valuation_data.get('confidence', ''),
                            valuation_data.get('low_value', ''),
                            valuation_data.get('estimate_value', ''),
                            valuation_data.get('high_value', ''),
                            valuation_data.get('rental_yield', '')
                        ))
                except Exception as e:
                    logger.error(f"Error inserting valuation for {valuation_field}: {e}")
        
        # Insert property history
        for history_field, history_type in [('Property_History_All', 'All'), ('Property_History_Sale', 'Sale'),
                                          ('Property_History_Listing', 'Listing'), ('Property_History_Rental', 'Rental'),
                                          ('Property_History_DA', 'DA')]:
            if property_data.get(history_field):
                try:
                    history_data = json.loads(property_data[history_field])
                    if history_data.get('events'):
                        # Clear existing history for this property and type
                        cursor.execute("DELETE FROM property_history WHERE property_id = %s AND history_type = %s", 
                                     (property_id, history_type))
                        
                        for event in history_data['events']:
                            history_query = """
                            INSERT INTO property_history (property_id, history_type, event_date, event_description,
                                                        event_details, properties_sold_12_months)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """
                            details = '; '.join(event.get('details', [])) if event.get('details') else ''
                            cursor.execute(history_query, (
                                property_id,
                                history_type,
                                event.get('date', ''),
                                event.get('description', ''),
                                details,
                                property_data.get('Properties_Sold_12_Months', '') if history_type == 'All' else ''
                            ))
                except Exception as e:
                    logger.error(f"Error inserting history for {history_field}: {e}")
        
        # Insert property attributes
        if property_data.get('Property_Attributes_JSON'):
            try:
                attributes_data = json.loads(property_data['Property_Attributes_JSON'])
                attributes_query = """
                INSERT INTO property_attributes (property_id, attributes_json)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE
                attributes_json = VALUES(attributes_json),
                updated_at = CURRENT_TIMESTAMP
                """
                cursor.execute(attributes_query, (property_id, property_data['Property_Attributes_JSON']))
            except Exception as e:
                logger.error(f"Error inserting property attributes: {e}")
        
        connection.commit()
        logger.info(f"Successfully inserted property data for: {property_data.get('Address', 'Unknown')}")
        return property_id
        
    except Error as e:
        logger.error(f"Database error: {e}")
        connection.rollback()
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def log_scraping_result(property_url, status, error_message=None, duration=None):
    """Log scraping result to database."""
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        log_query = """
        INSERT INTO scraping_logs (property_url, scraping_status, error_message, scraping_duration_seconds)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(log_query, (property_url, status, error_message, duration))
        connection.commit()
    except Error as e:
        logger.error(f"Error logging scraping result: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Import the extraction function from the original file
# (You'll need to copy the extract_property_data function from sales_scraping.py)
# For brevity, I'm including a simplified version here

def extract_property_data(driver, url):
    """Extract comprehensive property data from a single property page."""
    start_time = time.time()
    logger.info(f"🔍 Scraping property: {url}")
    
    try:
        logger.info(f"🌐 Loading URL: {url}")
        driver.get(url)
        
        # Wait for initial page load
        time.sleep(5)
        
        # Check if page loaded successfully
        current_url = driver.current_url
        logger.info(f"Current URL after load: {current_url}")
        
        # Check for common error pages or redirects
        if "error" in current_url.lower() or "404" in current_url.lower():
            logger.error("❌ Error page detected")
            return None
        
        # Wait for the main content to load with multiple attempts
        max_attempts = 5
        page_loaded = False
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"⏳ Waiting for page content (attempt {attempt + 1}/{max_attempts})")
                
                # Try multiple selectors for the main content
                selectors_to_try = [
                    (By.ID, "attr-single-line-address"),
                    (By.CSS_SELECTOR, "[data-testid='property-attr-bed']"),
                    (By.CSS_SELECTOR, ".image-gallery"),
                    (By.CSS_SELECTOR, "h4"),
                    (By.TAG_NAME, "body")
                ]
                
                for by, selector in selectors_to_try:
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((by, selector))
                        )
                        logger.info(f"✅ Found content with selector: {selector}")
                        page_loaded = True
                        break
                    except:
                        continue
                
                if page_loaded:
                    break
                    
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    logger.info(f"Retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    logger.warning("⚠️ Main content not loaded after all attempts, continuing anyway...")
        
        # Additional wait for dynamic content
        time.sleep(5)
        
        # Scroll to ensure all content is loaded
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
        except:
            pass
        
        # Initialize property data structure
        property_data = {
            'Property_URL': url,
            'Address': '',
            'Bedrooms': '',
            'Bathrooms': '',
            'Car_Spaces': '',
            'Land_Size': '',
            'Floor_Area': '',
            'Property_Type': '',
            'Last_Sold_Price': '',
            'Last_Sold_Date': '',
            'Sold_By': '',
            'Land_Use': '',
            'Issue_Date': '',
            'Advertisement_Date': '',
            'Listing_Description': '',
            'Advertising_Agent_Info_JSON': '',
            'Owner_Type': '',
            'Current_Tenure': '',
            'Title_Indicator': '',
            'LA': '',
            'Properties_Sold_12_Months': '',
            'Property_History_All': '',
            'Property_History_Sale': '',
            'Property_History_Listing': '',
            'Property_History_Rental': '',
            'Property_History_DA': '',
            'Natural_Risks': '',
            'Valuation_Estimate_Estimate': '',
            'Valuation_Estimate_Estimate_JSON': '',
            'Valuation_Estimate_Rental': '',
            'Valuation_Estimate_Rental_JSON': '',
            'Nearby_Schools_In_Catchment': '',
            'Nearby_Schools_All_Nearby': '',
            'Additional_Information_Legal_Description': '',
            'Additional_Information_Property_Features': '',
            'Additional_Information_Land_Values': '',
            'Household_Information_Owner_Information': '',
            'Household_Information_Marketing_Contacts': '',
            'Property_Attributes_JSON': '',
            'Sale_Information_JSON': '',
            'Natural_Risks_JSON': '',
            'Scraping_Date': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Extract address from URL instead of scraping
        try:
            # Parse address from URL: https://rpp.corelogic.com.au/property/440-323-greens-road-mambourin-vic-3024/57145835
            # Extract the part between '/property/' and the last '/'
            url_parts = url.split('/property/')
            if len(url_parts) > 1:
                address_part = url_parts[1].split('/')[0]  # Get part before the ID
                # Replace hyphens with spaces and capitalize
                address_text = address_part.replace('-', ' ').title()
                property_data['Address'] = address_text
                logger.info(f"  ✅ Address extracted from URL: {address_text}")
            else:
                property_data['Address'] = ''
                logger.error(f"  ❌ Could not parse address from URL: {url}")
        except Exception as e:
            property_data['Address'] = ''
            logger.error(f"  ❌ Address extraction from URL failed: {e}")
        
        # Extract property attributes (bedrooms, bathrooms, car spaces, land size, floor area) as JSON
        property_attributes = {}
        
        try:
            bed_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="property-attr-bed"] .property-attribute-val')
            bed_spans = bed_container.find_elements(By.TAG_NAME, 'span')
            if len(bed_spans) > 1:
                bedrooms = bed_spans[1].text.strip()
                property_data['Bedrooms'] = bedrooms
                property_attributes['bedrooms'] = bedrooms
            else:
                property_data['Bedrooms'] = '-'
                property_attributes['bedrooms'] = '-'
            logger.info(f"  ✅ Bedrooms extracted: {property_data['Bedrooms']}")
        except Exception as e:
            property_data['Bedrooms'] = '-'
            property_attributes['bedrooms'] = '-'
            logger.error(f"  ❌ Bedrooms extraction failed: {e}")
            
        try:
            bath_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="property-attr-bath"] .property-attribute-val')
            bath_spans = bath_container.find_elements(By.TAG_NAME, 'span')
            if len(bath_spans) > 1:
                bathrooms = bath_spans[1].text.strip()
                property_data['Bathrooms'] = bathrooms
                property_attributes['bathrooms'] = bathrooms
            else:
                property_data['Bathrooms'] = '-'
                property_attributes['bathrooms'] = '-'
        except:
            property_data['Bathrooms'] = '-'
            property_attributes['bathrooms'] = '-'
            
        try:
            car_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="property-attr-car"] .property-attribute-val')
            car_spans = car_container.find_elements(By.TAG_NAME, 'span')
            if len(car_spans) > 1:
                car_spaces = car_spans[1].text.strip()
                property_data['Car_Spaces'] = car_spaces
                property_attributes['car_spaces'] = car_spaces
            else:
                property_data['Car_Spaces'] = '-'
                property_attributes['car_spaces'] = '-'
        except:
            property_data['Car_Spaces'] = '-'
            property_attributes['car_spaces'] = '-'
            
        try:
            land_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="val-land-area"]')
            land_spans = land_container.find_elements(By.TAG_NAME, 'span')
            if len(land_spans) > 1:
                land_size = land_spans[1].text.strip()
                property_data['Land_Size'] = land_size
                property_attributes['land_size'] = land_size
            else:
                property_data['Land_Size'] = '-'
                property_attributes['land_size'] = '-'
        except:
            property_data['Land_Size'] = '-'
            property_attributes['land_size'] = '-'
            
        try:
            floor_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="val-floor-area"]')
            floor_spans = floor_container.find_elements(By.TAG_NAME, 'span')
            if len(floor_spans) > 1:
                floor_area = floor_spans[1].text.strip()
                property_data['Floor_Area'] = floor_area
                property_attributes['floor_area'] = floor_area
            else:
                property_data['Floor_Area'] = '-'
                property_attributes['floor_area'] = '-'
        except:
            property_data['Floor_Area'] = '-'
            property_attributes['floor_area'] = '-'
        
        # Store property attributes as JSON
        property_data['Property_Attributes_JSON'] = json.dumps(property_attributes)
        
        # Extract property type
        property_type = safe_get_text(driver, By.ID, "attr-property-type")
        property_data['Property_Type'] = property_type
        
        # Extract sale information as JSON
        try:
            sale_data = {}
            sale_price_elem = driver.find_element(By.CSS_SELECTOR, '.sale-price')
            sale_text = sale_price_elem.text.strip()
            # Extract price and date from text like "Last Sold on 01 May 2025 for $227,000,000"
            price_match = re.search(r'\$([0-9,]+)', sale_text)
            date_match = re.search(r'(\d{1,2} \w+ \d{4})', sale_text)
            
            if price_match:
                sale_data['price'] = price_match.group(1).replace(',', '')
                property_data['Last_Sold_Price'] = price_match.group(1).replace(',', '')
            if date_match:
                sale_data['date'] = date_match.group(1)
                property_data['Last_Sold_Date'] = date_match.group(1)
            
            # Store as JSON for structured access
            if sale_data:
                property_data['Sale_Information_JSON'] = json.dumps(sale_data)
        except:
            pass
        
        # Extract sale details
        try:
            sold_by = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="sale-detail-sold-by"] .property-attribute-val')
            property_data['Sold_By'] = sold_by
        except:
            pass
            
        try:
            land_use = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="sale-detail-land-use"] .property-attribute-val')
            property_data['Land_Use'] = land_use
        except:
            pass
            
        try:
            issue_date = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="sale-detail-issue-date"] .property-attribute-val')
            property_data['Issue_Date'] = issue_date
        except:
            pass
        
        # Extract advertisement date
        try:
            ad_date = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="advertisement-date"] .attr-value')
            property_data['Advertisement_Date'] = ad_date
        except:
            pass
        
        # Extract listing description with "Show More" functionality
        try:
            # First try to find the listing description element
            desc_elem = driver.find_element(By.CSS_SELECTOR, '[data-testid="listing-desc"]')
            
            # Check if there's a "Show More" link and click it to get full description
            try:
                show_more_link = desc_elem.find_element(By.CSS_SELECTOR, 'a[href="#"], .show-more, [data-testid="show-more"]')
                if show_more_link and show_more_link.is_displayed():
                    logger.info("  🔍 Found 'Show More' link, clicking to expand description...")
                    driver.execute_script("arguments[0].click();", show_more_link)
                    time.sleep(2)  # Wait for content to expand
            except NoSuchElementException:
                # No "Show More" link found, continue with current content
                pass
            
            # Get the full description text
            property_data['Listing_Description'] = desc_elem.text.strip()
            logger.info(f"  ✅ Listing description extracted: {len(property_data['Listing_Description'])} characters")
        except Exception as e:
            logger.error(f"  ❌ Listing description extraction failed: {e}")
            property_data['Listing_Description'] = ''
        
        # Extract advertising agent information from listing description
        try:
            # Look for advertising agent information in the listing description area
            agent_info = {}
            
            # Try multiple selectors for advertising agency
            agency_selectors = [
                '[data-testid="listing-desc"] .advertising-agency',
                '.listing-desc .advertising-agency',
                '[data-testid="listing-desc"] .agency',
                '.listing-desc .agency',
                '[data-testid="listing-desc"] .advertising-agency-name',
                '.listing-desc .advertising-agency-name'
            ]
            
            for selector in agency_selectors:
                try:
                    agency_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    if agency_elem and agency_elem.text.strip():
                        agent_info['advertising_agency'] = agency_elem.text.strip()
                        break
                except NoSuchElementException:
                    continue
            
            # Try multiple selectors for advertising agent name
            agent_selectors = [
                '[data-testid="listing-desc"] .advertising-agent',
                '.listing-desc .advertising-agent',
                '[data-testid="listing-desc"] .agent-name',
                '.listing-desc .agent-name',
                '[data-testid="listing-desc"] .advertising-agent-name',
                '.listing-desc .advertising-agent-name'
            ]
            
            for selector in agent_selectors:
                try:
                    agent_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    if agent_elem and agent_elem.text.strip():
                        agent_info['advertising_agent'] = agent_elem.text.strip()
                        break
                except NoSuchElementException:
                    continue
            
            # Try multiple selectors for agent phone number
            phone_selectors = [
                '[data-testid="listing-desc"] .agent-phone',
                '.listing-desc .agent-phone',
                '[data-testid="listing-desc"] .phone',
                '.listing-desc .phone',
                '[data-testid="listing-desc"] .agent-phone-number',
                '.listing-desc .agent-phone-number'
            ]
            
            for selector in phone_selectors:
                try:
                    phone_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    if phone_elem and phone_elem.text.strip():
                        agent_info['agent_phone'] = phone_elem.text.strip()
                        break
                except NoSuchElementException:
                    continue
            
            # If no agent info found via selectors, try to extract from listing description text
            if not agent_info and property_data.get('Listing_Description'):
                try:
                    desc_text = property_data['Listing_Description']
                    
                    # Look for common patterns in the description text
                    import re
                    
                    # First, try to find the agent section by looking for "Advertising Agency" label
                    agency_section_match = re.search(r'Advertising Agency[:\s]*([^\n\r]+)', desc_text, re.IGNORECASE)
                    if agency_section_match:
                        agent_info['advertising_agency'] = agency_section_match.group(1).strip()
                    
                    # Look for "Advertising Agent" label
                    agent_section_match = re.search(r'Advertising Agent[:\s]*([^\n\r]+)', desc_text, re.IGNORECASE)
                    if agent_section_match:
                        agent_info['advertising_agent'] = agent_section_match.group(1).strip()
                    
                    # Look for "Agent Phone Number" label
                    phone_section_match = re.search(r'Agent Phone Number[:\s]*([^\n\r]+)', desc_text, re.IGNORECASE)
                    if phone_section_match:
                        agent_info['agent_phone'] = phone_section_match.group(1).strip()
                    
                    # If we found structured data, skip the pattern matching
                    if agent_info:
                        logger.info(f"  ✅ Found structured agent info in description")
                    else:
                        # Fallback to pattern matching if structured labels not found
                        logger.info(f"  🔍 Using pattern matching fallback for agent info")
                        
                        # Look for phone number patterns
                        phone_patterns = [
                            r'(\d{4}\s\d{3}\s\d{3})',  # 0439 431 020
                            r'(\d{4}\s\d{3}\s\d{3})',  # 0451 065 565
                            r'(\d{10})',  # 0439431020
                            r'(\d{4}\.\d{3}\.\d{3})'   # 0439.431.020
                        ]
                        
                        for pattern in phone_patterns:
                            phone_match = re.search(pattern, desc_text)
                            if phone_match:
                                agent_info['agent_phone'] = phone_match.group(1)
                                break
                        
                        # Look for agency names (more specific patterns)
                        agency_patterns = [
                            r'(RT Edgar \w+)',
                            r'([A-Z][a-z]+\s+[A-Z][a-z]+\s+(?:Realty|Property|Estate|Group|Agency))',
                            r'([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+)'  # Three word agency names
                        ]
                        
                        for pattern in agency_patterns:
                            agency_match = re.search(pattern, desc_text)
                            if agency_match:
                                agency_name = agency_match.group(1)
                                # Filter out common false positives
                                if not any(word in agency_name.lower() for word in ['expressions', 'interest', 'closing', 'monday', 'september', 'melbourne', 'location', 'access', 'public', 'transport']):
                                    agent_info['advertising_agency'] = agency_name
                                    break
                        
                        # Look for agent names (more specific patterns)
                        agent_patterns = [
                            r'(Sarah Case|Will Hocking)',  # Specific known agents
                            r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'  # General name pattern
                        ]
                        
                        for pattern in agent_patterns:
                            agent_match = re.search(pattern, desc_text)
                            if agent_match:
                                agent_name = agent_match.group(1)
                                # Filter out common false positives
                                if not any(word in agent_name.lower() for word in ['expressions', 'interest', 'closing', 'monday', 'september', 'melbourne', 'location', 'access', 'public', 'transport', 'victorian', 'terrace', 'soaring', 'ceilings', 'retaining', 'original', 'features', 'pressed', 'metal', 'ornate', 'cornice', 'stain', 'glass', 'windows', 'tessellated', 'tiles', 'arched', 'entry', 'hall']):
                                    agent_info['advertising_agent'] = agent_name
                                    break
                    
                except Exception as text_extract_error:
                    logger.error(f"  ⚠️ Text-based agent extraction failed: {text_extract_error}")
            
            # Store agent information as JSON if found
            if agent_info:
                property_data['Advertising_Agent_Info_JSON'] = json.dumps(agent_info)
                logger.info(f"  ✅ Advertising agent info extracted: {len(agent_info)} fields")
            else:
                property_data['Advertising_Agent_Info_JSON'] = ''
                logger.info(f"  ℹ️ No advertising agent information found")
        except Exception as e:
            logger.error(f"  ⚠️ Advertising agent info extraction failed: {e}")
            property_data['Advertising_Agent_Info_JSON'] = ''
        
        # [Continue with the rest of the extraction logic from the original file...]
        # For brevity, I'm including the key parts. You'll need to copy the complete
        # extraction logic from sales_scraping.py for all the other sections.
        
        logger.info(f"✅ Successfully scraped property data")
        return property_data
        
    except Exception as e:
        logger.error(f"❌ Error scraping property {url}: {e}")
        return None

def scrape_all_properties_to_db():
    """Main function to scrape all properties and store in database."""
    
    # Read the CSV file with property URLs
    try:
        # df_links = pd.read_csv('vic_links.csv')
        # urls = df_links['Property_URL'].dropna().tolist()
        urls = ['https://rpp.corelogic.com.au/property/47-wellington-parade-south-east-melbourne-vic-3002/17241185']
        logger.info(f"📋 Found {len(urls)} property URLs to scrape")
    except Exception as e:
        logger.error(f"❌ Error reading vic_links.csv: {e}")
        return
    
    # Setup Chrome driver
    options = Options()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(600)
    driver.set_script_timeout(600)
    
    try:
        # Login first
        logger.info("🔐 Starting login process...")
        driver.get("https://rpp.corelogic.com.au/")
        logger.info("✅ Login page loaded")
        
        # Wait for page to fully load
        time.sleep(3)
        
        # Check if we're already logged in
        try:
            current_url = driver.current_url
            logger.info(f"Current URL after login page load: {current_url}")
            
            # If we're redirected to a different page, we might already be logged in
            if "login" not in current_url.lower() and "signin" not in current_url.lower():
                logger.info("✅ Already logged in or redirected to main page")
            else:
                logger.info("🔐 Proceeding with login...")
                
                username_field = wait_until_present(driver, By.ID, "username", timeout=10)
                username_field.clear()
                username_field.send_keys("delpg2021")
                logger.info("✅ Username entered")
                
                password_field = wait_until_present(driver, By.ID, "password", timeout=10)
                password_field.clear()
                password_field.send_keys("FlatHead@2024")
                logger.info("✅ Password entered")
                
                sign_on_button = wait_until_clickable(driver, By.ID, "signOnButton", timeout=10)
                sign_on_button.click()
                logger.info("✅ Login button clicked")
                
                # Wait for login to complete and check for redirect
                time.sleep(20)
                current_url = driver.current_url
                logger.info(f"URL after login attempt: {current_url}")
                
        except Exception as login_error:
            logger.error(f"⚠️ Login error: {login_error}")
            logger.info("Continuing anyway...")
        
        # Final wait to ensure we're ready
        time.sleep(3)
        
        # Scrape each property
        successful_scrapes = 0
        failed_scrapes = 0
        
        for i, url in enumerate(urls, 1):
            logger.info(f"\n📊 Processing property {i}/{len(urls)}")
            start_time = time.time()
            
            try:
                property_data = extract_property_data(driver, url)
                if property_data:
                    # Store in database
                    property_id = insert_property_data(property_data)
                    if property_id:
                        successful_scrapes += 1
                        duration = int(time.time() - start_time)
                        log_scraping_result(url, 'Success', duration=duration)
                        logger.info(f"✅ Successfully stored property {property_id} in database")
                    else:
                        failed_scrapes += 1
                        duration = int(time.time() - start_time)
                        log_scraping_result(url, 'Failed', 'Database insertion failed', duration)
                        logger.error(f"❌ Failed to store property in database")
                else:
                    failed_scrapes += 1
                    duration = int(time.time() - start_time)
                    log_scraping_result(url, 'Failed', 'Data extraction failed', duration)
                    logger.error(f"❌ Failed to extract property data")
                
            except Exception as e:
                failed_scrapes += 1
                duration = int(time.time() - start_time)
                log_scraping_result(url, 'Failed', str(e), duration)
                logger.error(f"❌ Error processing property: {e}")
            
            # Add delay between requests to be respectful
            time.sleep(2)
        
        logger.info(f"\n📊 Scraping Summary:")
        logger.info(f"  - Total properties processed: {len(urls)}")
        logger.info(f"  - Successful scrapes: {successful_scrapes}")
        logger.info(f"  - Failed scrapes: {failed_scrapes}")
        logger.info(f"  - Success rate: {(successful_scrapes/len(urls)*100):.1f}%")
            
    except Exception as e:
        logger.error(f"❌ Error during scraping process: {e}")
    finally:
        driver.quit()
        logger.info("🔚 Browser closed")

if __name__ == "__main__":
    # Test database connection first
    connection = get_db_connection()
    if connection:
        logger.info("✅ Database connection successful")
        connection.close()
        scrape_all_properties_to_db()
    else:
        logger.error("❌ Database connection failed. Please check your configuration.")
