from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import time
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
import json
import re
from dotenv import load_dotenv
load_dotenv()

# Import comprehensive extraction function
from comprehensive_extraction import extract_comprehensive_property_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Helper functions ---
def wait_until_clickable(driver, by, value, check_interval=0.5, timeout=None):
    """Wait until an element is displayed and enabled (clickable)."""
    start = time.time()
    while True:
        try:
            elem = driver.find_element(by, value)
            if elem.is_displayed() and elem.is_enabled():
                return elem
        except (NoSuchElementException, ElementClickInterceptedException):
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
        except (NoSuchElementException, ElementClickInterceptedException):
            pass
        time.sleep(check_interval)
        if timeout and (time.time() - start) > timeout:
            raise TimeoutError(f"Element {value} not found after {timeout} seconds")

def safe_get_text(driver, by, value, default=""):
    """Safely get text from an element, return default if not found."""
    try:
        element = driver.find_element(by, value)
        return element.text.strip()
    except (NoSuchElementException, ElementClickInterceptedException):
        return default

def get_db_connection():
    """Get PostgreSQL database connection from environment variable."""
    try:
        print(os.getenv('DATABASE_URL'))
        connection = psycopg2.connect(os.getenv('DATABASE_URL'))
        logger.info("Successfully connected to PostgreSQL database")
        return connection
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {e}")
        return None

def insert_property_data(property_data):
    """Insert comprehensive property data into PostgreSQL database."""
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
        
        result = cursor.fetchone()
        property_id = result[0] if result else None
        
        # Insert sale/rental information
        sale_rental_fields = ['Last_Sold_Price', 'Last_Sold_Date', 'Sold_By', 'Land_Use', 'Issue_Date', 'Advertisement_Date', 'Listing_Description']
        has_sale_rental_data = any(property_data.get(field) for field in sale_rental_fields)
        
        logger.info(f"Sale/Rental data check:")
        for field in sale_rental_fields:
            value = property_data.get(field, '')
            logger.info(f"  {field}: {value[:100] if value else 'None'}...")
        
        if has_sale_rental_data:
            # First delete existing record if it exists
            cursor.execute("DELETE FROM sale_rental_info WHERE property_id = %s", (property_id,))
            
            sale_rental_query = """
            INSERT INTO sale_rental_info (property_id, last_sold_price, last_sold_date, sold_by, land_use,
                                        issue_date, advertisement_date, listing_description, advertising_agency,
                                        advertising_agent, agent_phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Parse advertising agent info from JSON (handle both single agent and array of agents)
            advertising_agency = ''
            advertising_agent = ''
            agent_phone = ''
            if property_data.get('Advertising_Agent_Info_JSON'):
                try:
                    agent_info = json.loads(property_data['Advertising_Agent_Info_JSON'])
                    
                    # Handle array of agents (new format)
                    if isinstance(agent_info, list) and len(agent_info) > 0:
                        first_agent = agent_info[0]
                        advertising_agency = first_agent.get('advertising_agency', '')
                        advertising_agent = first_agent.get('advertising_agent', '')
                        agent_phone = first_agent.get('agent_phone', '')
                    # Handle single agent object (old format)
                    elif isinstance(agent_info, dict):
                        advertising_agency = agent_info.get('advertising_agency', '')
                        advertising_agent = agent_info.get('advertising_agent', '')
                        agent_phone = agent_info.get('agent_phone', '')
                except Exception as e:
                    logger.error(f"Error parsing advertising agent info: {e}")
                    pass
            
            logger.info(f"Inserting sale/rental data:")
            logger.info(f"  Advertisement Date: {property_data.get('Advertisement_Date', '')}")
            logger.info(f"  Listing Description: {property_data.get('Listing_Description', '')[:100]}...")
            logger.info(f"  Advertising Agency: {advertising_agency}")
            logger.info(f"  Advertising Agent: {advertising_agent}")
            logger.info(f"  Agent Phone: {agent_phone}")
            
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
        
        # Insert household information
        if any(property_data.get(field) for field in ['Household_Information_Owner_Information', 'Household_Information_Marketing_Contacts']):
            # First delete existing record if it exists
            cursor.execute("DELETE FROM household_info WHERE property_id = %s", (property_id,))
            
            household_query = """
            INSERT INTO household_info (property_id, owner_information, marketing_contacts)
            VALUES (%s, %s, %s)
            """
            cursor.execute(household_query, (
                property_id,
                property_data.get('Household_Information_Owner_Information', ''),
                property_data.get('Household_Information_Marketing_Contacts', '')
            ))
        
        # Insert additional information
        if any(property_data.get(field) for field in ['Additional_Information_Legal_Description', 'Additional_Information_Property_Features', 'Additional_Information_Land_Values']):
            # First delete existing record if it exists
            cursor.execute("DELETE FROM additional_info WHERE property_id = %s", (property_id,))
            
            additional_query = """
            INSERT INTO additional_info (property_id, legal_description, property_features, land_values)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(additional_query, (
                property_id,
                property_data.get('Additional_Information_Legal_Description', ''),
                property_data.get('Additional_Information_Property_Features', ''),
                property_data.get('Additional_Information_Land_Values', '')
            ))
        
        # Insert property attributes
        if property_data.get('Property_Attributes_JSON'):
            # First delete existing record if it exists
            cursor.execute("DELETE FROM property_attributes WHERE property_id = %s", (property_id,))
            
            attributes_query = """
            INSERT INTO property_attributes (property_id, attributes_json)
            VALUES (%s, %s)
            """
            cursor.execute(attributes_query, (
                property_id,
                property_data.get('Property_Attributes_JSON', '{}')
            ))
        
        # Insert property history
        history_types = {
            'Property_History_All': 'All',
            'Property_History_Sale': 'Sale',
            'Property_History_Listing': 'Listing',
            'Property_History_Rental': 'Rental',
            'Property_History_DA': 'DA'
        }
        
        for history_field, history_type in history_types.items():
            if property_data.get(history_field):
                try:
                    history_data = json.loads(property_data[history_field])
                    if history_data:
                        # Clear existing history for this property and type
                        cursor.execute("DELETE FROM property_history WHERE property_id = %s AND history_type = %s", 
                                     (property_id, history_type))
                        
                        for event in history_data.get('events', []):
                            history_query = """
                            INSERT INTO property_history (property_id, history_type, event_date, event_description, event_details)
                            VALUES (%s, %s, %s, %s, %s)
                            """
                            cursor.execute(history_query, (
                                property_id,
                                history_type,
                                event.get('date', ''),
                                event.get('description', ''),
                                event.get('details', '')
                            ))
                except Exception as e:
                    logger.error(f"Error inserting property history for {history_field}: {e}")
        
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
        
        connection.commit()
        logger.info(f"Successfully inserted comprehensive property data for: {property_data.get('Address', 'Unknown')}")
        return property_id
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        connection.rollback()
        return None
    finally:
        if connection:
            cursor.close()
            connection.close()

# Old extraction function removed - using comprehensive_extraction.py instead

def search_and_scrape_property_by_address(address):
    """
    Main function to search for a property by address and scrape its data.
    
    Args:
        address (str): The address to search for
        
    Returns:
        dict: JSON response with success status and property data
    """
    logger.info(f"🏠 Starting property search for address: {address}")
    
    # Setup Chrome driver
    options = Options()
    options.add_experimental_option("detach", True)  # Keep browser open
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(600)
    driver.set_script_timeout(600)
    
    try:
        # Step 1: Login
        logger.info("🔐 Starting login process...")
        driver.get("https://rpp.corelogic.com.au/")
        logger.info("✅ Login page loaded")
        
        # Wait for page to fully load
        time.sleep(8)
        
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
                
                # Wait for login to complete
                time.sleep(8)
                current_url = driver.current_url
                logger.info(f"URL after login attempt: {current_url}")
                
                # Handle terms and conditions page if redirected there
                if "terms-and-conditions" in current_url:
                    logger.info("📋 Terms and conditions page detected, accepting...")
                    try:
                        # Look for accept button or checkbox
                        accept_button = wait_until_clickable(driver, By.CSS_SELECTOR, "button[type='submit'], .accept-button, .btn-primary", timeout=10)
                        accept_button.click()
                        logger.info("✅ Terms and conditions accepted")
                        time.sleep(3)
                        
                        # Wait for redirect to main page
                        current_url = driver.current_url
                        logger.info(f"URL after accepting terms: {current_url}")
                    except Exception as terms_error:
                        logger.error(f"⚠️ Could not accept terms: {terms_error}")
                        logger.info("Continuing anyway...")
                
        except Exception as login_error:
            logger.error(f"⚠️ Login error: {login_error}")
            logger.info("Continuing anyway...")
        
        # Wait for main page to fully load before proceeding
        logger.info("⏳ Waiting for main page to load completely...")
        time.sleep(5)
        
        # Step 2: Click the burger menu
        logger.info("🍔 Clicking burger menu...")
        try:
            # Wait for the burger menu to be present and clickable
            burger_menu = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.rpd-burger-menu"))
            )
            burger_menu.click()
            logger.info("✅ Burger menu clicked")
            time.sleep(2)  # Wait for menu to open
        except Exception as e:
            logger.error(f"❌ Failed to click burger menu: {e}")
            driver.quit()
            return {
                'success': False,
                'message': f'Failed to click burger menu: {str(e)}',
                'data': None
            }
        
        # Step 3: Enter address in search bar
        logger.info(f"🔍 Entering address in search bar: {address}")
        try:
            # Wait for search input to be present and interactable
            search_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "crux-multi-locality-search"))
            )
            search_input.clear()
            search_input.send_keys(address)
            logger.info("✅ Address entered in search bar")
            
            # Wait a moment to see if dropdown appears automatically
            time.sleep(2)
            
            # Check if dropdown options are already visible
            try:
                dropdown_options = driver.find_elements(By.CSS_SELECTOR, ".MuiAutocomplete-option, [role='option']")
                if not dropdown_options:
                    # If no dropdown options visible, click search bar to make dropdown appear
                    search_input.click()
                    logger.info("✅ Clicked search bar to show dropdown")
                    time.sleep(2)
                else:
                    logger.info("✅ Dropdown appeared automatically")
            except:
                # If we can't check, click search bar as fallback
                search_input.click()
                logger.info("✅ Clicked search bar as fallback")
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"❌ Failed to enter address in search bar: {e}")
            driver.quit()
            return {
                'success': False,
                'message': f'Failed to enter address in search bar: {str(e)}',
                'data': None
            }
        
        # Step 4: Click the first dropdown option
        logger.info("📋 Clicking first dropdown option...")
        try:
            # Wait for dropdown options to appear and click first option
            dropdown_option = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".MuiAutocomplete-option:first-child"))
            )
            dropdown_option.click()
            logger.info("✅ First dropdown option clicked")
            time.sleep(2)  # Wait for selection
        except Exception as e:
            logger.error(f"❌ Failed to click first dropdown option: {e}")
            # Try alternative selector
            try:
                dropdown_option = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[role='option']:first-child"))
                )
                dropdown_option.click()
                logger.info("✅ First dropdown option clicked (alternative selector)")
                time.sleep(2)
            except Exception as e2:
                logger.error(f"❌ Failed to click dropdown option with alternative selector: {e2}")
                driver.quit()
                return {
                    'success': False,
                    'message': f'Failed to click dropdown option: {str(e2)}',
                    'data': None
                }
        
        # Step 5: Wait for results page to load (search happens automatically after dropdown selection)
        logger.info("⏳ Waiting for results page to load...")
        time.sleep(8)
        
        # Step 6: Extract property data
        current_url = driver.current_url
        logger.info(f"Current URL after search: {current_url}")
        
        property_data = extract_comprehensive_property_data(driver, current_url)
        
        if property_data:
            # Step 7: Store in database
            logger.info("💾 Storing property data in database...")
            property_id = insert_property_data(property_data)
            
            if property_id:
                logger.info(f"✅ Successfully stored property {property_id} in database")
                property_data['id'] = property_id
                driver.quit()
                return {
                    'success': True,
                    'message': 'Property data scraped and saved successfully',
                    'data': property_data
                }
            else:
                logger.error("❌ Failed to store property in database")
                driver.quit()
                return {
                    'success': False,
                    'message': 'Failed to store property in database',
                    'data': property_data
                }
        else:
            logger.error("❌ Failed to extract property data")
            driver.quit()
            return {
                'success': False,
                'message': 'Failed to extract property data',
                'data': None
            }
            
    except Exception as e:
        logger.error(f"❌ Error during search and scrape process: {e}")
        driver.quit()
        return {
            'success': False,
            'message': f'Error during scraping: {str(e)}',
            'data': None
        }

# Example usage
if __name__ == "__main__":
    import sys
    
    # Check if address is provided as command line argument
    if len(sys.argv) > 1:
        address = sys.argv[1]
    else:
        address = "47 Wellington Parade South East Melbourne VIC 3002"  # Default test address
    
    # Test database connection first
    connection = get_db_connection()
    if connection:
        logger.info("✅ Database connection successful")
        connection.close()
        
        # Search for the address
        result = search_and_scrape_property_by_address(address)
        
        # Print JSON result
        print(json.dumps(result, indent=2))
        
        if result['success']:
            logger.info("✅ Address search completed successfully")
        else:
            logger.error("❌ Address search failed")
        
    else:
        logger.error("❌ Database connection failed. Please check your configuration.")
        print(json.dumps({
            'success': False,
            'message': 'Database connection failed',
            'data': None
        }, indent=2))
