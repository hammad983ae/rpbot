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
import difflib
import re

def _clean_text(value: str) -> str:
    if not isinstance(value, str):
        return value
    # Remove non-printable characters
    value = ''.join(ch for ch in value if ch.isprintable())
    # Normalize whitespace
    value = re.sub(r"\s+", " ", value).strip()
    # Remove stray slashes/backslashes at ends and duplicate slashes inside
    value = value.strip("/\\")
    value = re.sub(r"/{2,}", "/", value)
    return value

def _try_parse_json(value: str):
    if not value or not isinstance(value, str):
        return None
    try:
        return json.loads(value)
    except Exception:
        return None

def _clean_distance(value: str) -> str:
    value = _clean_text(value)
    if not value:
        return value
    # Ensure a space before km or m if missing (e.g., 0.82km -> 0.82 km)
    value = re.sub(r"(?i)(\d)\s*(km|m)\b", r"\1 \2", value)
    return value

def _transform_for_api(raw: dict) -> dict:
    """Normalize and sanitize fields returned to the frontend."""
    sanitized = {}
    get = raw.get

    sanitized['id'] = get('id')
    sanitized['propertyUrl'] = _clean_text(get('Property_URL', ''))
    sanitized['address'] = _clean_text(get('Address', ''))
    sanitized['type'] = _clean_text(get('Property_Type', ''))

    # Numeric-like strings remain as strings if unknown; frontend can coerce if needed
    sanitized['bedrooms'] = _clean_text(get('Bedrooms', ''))
    sanitized['bathrooms'] = _clean_text(get('Bathrooms', ''))
    sanitized['carSpaces'] = _clean_text(get('Car_Spaces', ''))
    sanitized['landSize'] = _clean_text(get('Land_Size', ''))
    sanitized['floorArea'] = _clean_text(get('Floor_Area', ''))

    sanitized['lastSold'] = {
        'price': _clean_text(get('Last_Sold_Price', '')),
        'date': _clean_text(get('Last_Sold_Date', '')),
        'soldBy': _clean_text(get('Sold_By', ''))
    }

    sanitized['sale'] = {
        'landUse': _clean_text(get('Land_Use', '')),
        'issueDate': _clean_text(get('Issue_Date', '')),
        'advertisementDate': _clean_text(get('Advertisement_Date', '')),
        'listingDescription': _clean_text(get('Listing_Description', ''))
    }

    # Agent info (handle both JSON format from scraping and individual fields from database)
    agent_json = get('Advertising_Agent_Info_JSON', '')
    agent = None
    
    # Try to parse JSON format first (from scraping)
    if agent_json:
        try:
            parsed = json.loads(agent_json) if agent_json else []
            if isinstance(parsed, list) and parsed:
                agent = parsed[0]
            elif isinstance(parsed, dict):
                agent = parsed
        except Exception:
            agent = None
    
    # If no JSON data, use individual fields from database
    if not agent:
        agent = {
            'advertising_agency': get('Advertising_Agency', ''),
            'advertising_agent': get('Advertising_Agent', ''),
            'agent_phone': get('Agent_Phone', '')
        }
    
    sanitized['agent'] = {
        'agency': _clean_text(agent.get('advertising_agency', '')),
        'name': _clean_text(agent.get('advertising_agent', '')),
        'phone': _clean_text(agent.get('agent_phone', '')),
    }

    # Additional info
    # Additional info: attempt to parse JSON-like strings into objects
    legal_desc_raw = get('Additional_Information_Legal_Description', '')
    features_raw = get('Additional_Information_Property_Features', '')
    land_values_raw = get('Additional_Information_Land_Values', '')

    legal_desc = _try_parse_json(legal_desc_raw) or _clean_text(legal_desc_raw)
    if isinstance(legal_desc, dict):
        legal_desc = { _clean_text(k): _clean_text(v) for k, v in legal_desc.items() }

    features = _try_parse_json(features_raw) or _clean_text(features_raw)
    if isinstance(features, dict):
        features = { _clean_text(k): _clean_text(v) for k, v in features.items() }

    land_values = _try_parse_json(land_values_raw) or _clean_text(land_values_raw)
    if isinstance(land_values, dict):
        land_values = { _clean_text(k): _clean_text(v) for k, v in land_values.items() }

    sanitized['additional'] = {
        'legalDescription': legal_desc,
        'features': features,
        'landValues': land_values,
    }

    # Household
    # Parse JSON fields for owner information and marketing contacts
    owner_info_raw = get('Household_Information_Owner_Information', '')
    marketing_contacts_raw = get('Household_Information_Marketing_Contacts', '')
    
    # Parse owner information JSON
    owner_info_parsed = _try_parse_json(owner_info_raw)
    if isinstance(owner_info_parsed, dict):
        # Extract individual fields from the JSON
        owner_name = owner_info_parsed.get('Name', '')
        owner_type = owner_info_parsed.get('Owner Type', '')
        current_tenure = owner_info_parsed.get('Current Tenure', '')
    else:
        owner_name = ''
        owner_type = ''
        current_tenure = ''
    
    # Parse marketing contacts JSON
    marketing_contacts_parsed = _try_parse_json(marketing_contacts_raw)
    if isinstance(marketing_contacts_parsed, dict):
        contacts = marketing_contacts_parsed.get('Contacts', [])
        if isinstance(contacts, list):
            marketing_contacts_display = ' • '.join(contacts)
        else:
            marketing_contacts_display = str(contacts)
    else:
        marketing_contacts_display = ''
    
    sanitized['household'] = {
        'ownerType': _clean_text(owner_type or get('Owner_Type', '')),
        'currentTenure': _clean_text(current_tenure or get('Current_Tenure', '')),
        'ownerName': _clean_text(owner_name),
        'ownerInformation': owner_info_parsed if owner_info_parsed else None,
        'marketingContacts': marketing_contacts_display,
        'marketingContactsRaw': marketing_contacts_parsed if marketing_contacts_parsed else None,
    }
    logger.info(f"🔍 Transformed household data: {sanitized['household']}")

    # Valuation
    estimate_json_raw = get('Valuation_Estimate_Estimate_JSON', '')
    rental_json_raw = get('Valuation_Estimate_Rental_JSON', '')

    estimate_json = _try_parse_json(estimate_json_raw)
    if isinstance(estimate_json, dict):
        estimate_json = { _clean_text(k): _clean_text(v) for k, v in estimate_json.items() }

    rental_json = _try_parse_json(rental_json_raw)
    if isinstance(rental_json, dict):
        rental_json = { _clean_text(k): _clean_text(v) for k, v in rental_json.items() }

    sanitized['valuation'] = {
        'estimate': _clean_text(get('Valuation_Estimate_Estimate', '')),
        'estimateJson': estimate_json or _clean_text(estimate_json_raw),
        'rental': _clean_text(get('Valuation_Estimate_Rental', '')),
        'rentalJson': rental_json or _clean_text(rental_json_raw),
    }

    # Schools
    def _parse_schools(field_name: str):
        arr_raw = get(field_name, '')
        parsed = _try_parse_json(arr_raw)
        if isinstance(parsed, list):
            cleaned_list = []
            for s in parsed:
                if not isinstance(s, dict):
                    continue
                attrs = s.get('attributes', {}) if isinstance(s.get('attributes'), dict) else {}
                cleaned_list.append({
                    'name': _clean_text(s.get('name', '')),
                    'address': _clean_text(s.get('address', '')),
                    'distance': _clean_distance(s.get('distance', '')),
                    'attributes': {
                        'type': _clean_text(attrs.get('type', '')),
                        'sector': _clean_text(attrs.get('sector', '')),
                        'gender': _clean_text(attrs.get('gender', '')),
                        'year_levels': _clean_text(attrs.get('year_levels', '')),
                        'enrollments': _clean_text(attrs.get('enrollments', '')),
                    }
                })
            return cleaned_list
        # Fallback to cleaned string
        return _clean_text(arr_raw)

    sanitized['schools'] = {
        'inCatchment': _parse_schools('Nearby_Schools_In_Catchment'),
        'allNearby': _parse_schools('Nearby_Schools_All_Nearby'),
    }

    # Property history - handle both database format (Property_History_All) and scraped format (separate fields)
    history_raw = get('Property_History_All', '')
    history_data = _try_parse_json(history_raw)
    
    logger.info(f"🔍 History transformation - Property_History_All: {history_raw[:200] if history_raw else 'None'}...")
    
    # Debug: Check what history fields are available in the raw data
    history_fields = ['Property_History_All', 'Property_History_Sale', 'Property_History_Listing', 'Property_History_Rental', 'Property_History_DA']
    for field in history_fields:
        field_value = get(field, '')
        logger.info(f"🔍 Raw data - {field}: {field_value[:100] if field_value else 'None'}...")
    
    if history_data:
        # Data from database - already in the correct format
        logger.info(f"🔍 Using database history format: {history_data}")
        sanitized['history'] = history_data
    else:
        # Data from scraping - check if Property_History_All has the correct structure
        logger.info("🔍 No Property_History_All found, checking scraped history fields...")
        
        # First, check if any of the individual history fields contain the full structure
        history_fields_to_check = ['Property_History_All', 'Property_History_Sale', 'Property_History_Listing', 'Property_History_Rental', 'Property_History_DA']
        found_structured_data = None
        
        for field in history_fields_to_check:
            field_data = get(field, '')
            if field_data:
                try:
                    parsed_data = json.loads(field_data)
                    logger.info(f"🔍 Checking {field}: {parsed_data}")
                    
                    # Check if this field contains the full structured data with events_by_type
                    if isinstance(parsed_data, dict) and 'events_by_type' in parsed_data and 'total_events' in parsed_data:
                        logger.info(f"🔍 Found structured history data in {field}: {parsed_data}")
                        found_structured_data = parsed_data
                        break
                    # Check if this field contains events array (from comprehensive_extraction.py)
                    elif isinstance(parsed_data, dict) and 'events' in parsed_data and 'events_by_type' in parsed_data:
                        logger.info(f"🔍 Found comprehensive extraction format in {field}: {parsed_data}")
                        found_structured_data = parsed_data
                        break
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse {field}: {e}")
        
        if found_structured_data:
            # Normalize the structured data to match database format
            # Remove the 'events' array if it exists (comprehensive_extraction.py format)
            # Keep only 'events_by_type' and 'total_events' (database format)
            normalized_data = {
                'events_by_type': found_structured_data.get('events_by_type', {}),
                'total_events': found_structured_data.get('total_events', 0)
            }
            
            # Remove any extra fields that aren't in the database format
            sanitized['history'] = normalized_data
            logger.info(f"🔍 Using normalized structured history data: {normalized_data}")
            logger.info(f"🔍 Normalized data has {normalized_data.get('total_events', 0)} total events")
            for event_type, events in normalized_data.get('events_by_type', {}).items():
                logger.info(f"🔍 Normalized {event_type} events: {len(events)}")
        else:
            # Fallback: try to combine separate history fields (old method)
            logger.info("🔍 No structured data found, attempting to combine individual fields...")
            events_by_type = {
                'sale': [],
                'rental': [],
                'listing': [],
                'da': [],
                'other': []
            }
            
            # Map scraped history fields to our format
            history_field_mapping = {
                'Property_History_Sale': 'sale',
                'Property_History_Listing': 'listing', 
                'Property_History_Rental': 'rental',
                'Property_History_DA': 'da'
            }
            
            total_events = 0
            for field, type_key in history_field_mapping.items():
                field_data = get(field, '')
                logger.info(f"🔍 Checking {field}: {field_data[:200] if field_data else 'None'}...")
                if field_data:
                    try:
                        parsed_data = json.loads(field_data)
                        logger.info(f"🔍 Parsed {field} data: {parsed_data}")
                        if isinstance(parsed_data, dict) and 'events' in parsed_data:
                            events = parsed_data['events']
                            events_by_type[type_key] = events
                            total_events += len(events)
                            logger.info(f"🔍 Loaded {len(events)} {type_key} events from scraped data")
                        else:
                            logger.warning(f"⚠️ {field} data doesn't have 'events' key or is not a dict: {type(parsed_data)}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to parse {field}: {e}")
                else:
                    logger.info(f"🔍 {field} is empty or None")
            
            sanitized['history'] = {
                'total_events': total_events,
                'events_by_type': events_by_type
            }
            
            logger.info(f"🔍 Final combined scraped history: {sanitized['history']}")
            logger.info(f"🔍 Combined scraped history: {total_events} total events across all types")

    sanitized['scrapedAt'] = _clean_text(get('Scraping_Date', ''))

    # Final debug logging for history data
    if 'history' in sanitized:
        logger.info(f"🔍 Final API response history data: {sanitized['history']}")
        logger.info(f"🔍 Final history total_events: {sanitized['history'].get('total_events', 0)}")
        if 'events_by_type' in sanitized['history']:
            for event_type, events in sanitized['history']['events_by_type'].items():
                logger.info(f"🔍 Final {event_type} events: {len(events)}")
    else:
        logger.warning("⚠️ No history data in final API response")

    return sanitized
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
        
        # Natural risks feature removed
        
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
    
    last_error = None
    
    # 0) Check DB for an existing property with ~85% similar address
    try:
        connection = psycopg2.connect(os.getenv('DATABASE_URL'))
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            # Prefer DB-side similarity if pg_trgm is available
            try:
                cursor.execute("SELECT id, property_url, address, similarity FROM GetMostSimilarProperty(%s, %s)", (address, 0.0))
                best_match = cursor.fetchone()
                best_ratio = float(best_match.get('similarity', 0)) if best_match else 0.0
                if best_match:
                    # Fetch complete property data for the matched property
                    cursor.execute("SELECT * FROM properties WHERE id = %s", (best_match.get('id'),))
                    best = cursor.fetchone()
            except Exception:
                # Fallback: fetch all and compare in Python
                cursor.execute("SELECT * FROM properties")
                rows = cursor.fetchall() or []
                def _norm(s: str) -> str:
                    return re.sub(r"\s+", " ", (s or '').lower()).strip()
                best = None
                best_ratio = 0.0
                for row in rows:
                    ratio = difflib.SequenceMatcher(None, _norm(address), _norm(row.get('address',''))).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best = row
            if best and best_ratio >= 0.85:
                logger.info(f"✅ Found existing property in DB with similarity {best_ratio:.3f}: {best.get('address','')}")
                # Build API response from DB by joining related tables
                prop_id = best['id']
                # Fetch related data for transformation
                # sale_rental_info
                cursor.execute("SELECT * FROM sale_rental_info WHERE property_id = %s LIMIT 1", (prop_id,))
                sri = cursor.fetchone() or {}
                # additional_info
                cursor.execute("SELECT * FROM additional_info WHERE property_id = %s LIMIT 1", (prop_id,))
                ai = cursor.fetchone() or {}
                # household_info
                cursor.execute("SELECT * FROM household_info WHERE property_id = %s LIMIT 1", (prop_id,))
                hi = cursor.fetchone() or {}
                logger.info(f"🔍 Household info retrieved: {hi}")
                # valuation_estimates
                cursor.execute("SELECT * FROM valuation_estimates WHERE property_id = %s", (prop_id,))
                ve_rows = cursor.fetchall() or []
                # nearby_schools
                cursor.execute("SELECT * FROM nearby_schools WHERE property_id = %s", (prop_id,))
                ns_rows = cursor.fetchall() or []
                # property_attributes
                cursor.execute("SELECT * FROM property_attributes WHERE property_id = %s LIMIT 1", (prop_id,))
                pa = cursor.fetchone() or {}
                # property_history
                cursor.execute("SELECT * FROM property_history WHERE property_id = %s ORDER BY event_date DESC", (prop_id,))
                ph_rows = cursor.fetchall() or []

                # Construct raw-like dict for _transform_for_api
                raw = {
                    'id': prop_id,
                    'Property_URL': best.get('property_url',''),
                    'Address': best.get('address',''),
                    'Property_Type': best.get('property_type',''),
                    'Bedrooms': best.get('bedrooms',''),
                    'Bathrooms': best.get('bathrooms',''),
                    'Car_Spaces': best.get('car_spaces',''),
                    'Land_Size': best.get('land_size',''),
                    'Floor_Area': best.get('floor_area',''),
                    'Last_Sold_Price': sri.get('last_sold_price',''),
                    'Last_Sold_Date': sri.get('last_sold_date',''),
                    'Sold_By': sri.get('sold_by',''),
                    'Land_Use': sri.get('land_use',''),
                    'Issue_Date': sri.get('issue_date',''),
                    'Advertisement_Date': sri.get('advertisement_date',''),
                    'Listing_Description': sri.get('listing_description',''),
                    'Advertising_Agency': sri.get('advertising_agency',''),
                    'Advertising_Agent': sri.get('advertising_agent',''),
                    'Agent_Phone': sri.get('agent_phone',''),
                    'Additional_Information_Legal_Description': ai.get('legal_description',''),
                    'Additional_Information_Property_Features': ai.get('property_features',''),
                    'Additional_Information_Land_Values': ai.get('land_values',''),
                    'Owner_Type': hi.get('owner_type',''),
                    'Current_Tenure': hi.get('current_tenure',''),
                    'Household_Information_Owner_Information': hi.get('owner_information',''),
                    'Household_Information_Marketing_Contacts': hi.get('marketing_contacts',''),
                    'Valuation_Estimate_Estimate': '',
                    'Valuation_Estimate_Estimate_JSON': '',
                    'Valuation_Estimate_Rental': '',
                    'Valuation_Estimate_Rental_JSON': '',
                    'Nearby_Schools_In_Catchment': '[]',
                    'Nearby_Schools_All_Nearby': '[]',
                    'Property_Attributes_JSON': pa.get('attributes_json','{}'),
                    'Property_History_All': '[]',
                    'Scraping_Date': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                # Populate valuation details
                for ve in ve_rows:
                    if (ve.get('estimate_type') or '').lower() == 'property valuation':
                        raw['Valuation_Estimate_Estimate_JSON'] = json.dumps({
                            'confidence': ve.get('confidence_level',''),
                            'low_value': ve.get('low_value',''),
                            'estimate_value': ve.get('estimate_value',''),
                            'high_value': ve.get('high_value','')
                        })
                    elif (ve.get('estimate_type') or '').lower() == 'rental estimate':
                        raw['Valuation_Estimate_Rental_JSON'] = json.dumps({
                            'confidence': ve.get('confidence_level',''),
                            'low_value': ve.get('low_value',''),
                            'estimate_value': ve.get('estimate_value',''),
                            'high_value': ve.get('high_value',''),
                            'rental_yield': ve.get('rental_yield','')
                        })
                # Schools arrays by catchment
                in_catch = []
                all_near = []
                for ns in ns_rows:
                    school_obj = {
                        'name': ns.get('school_name',''),
                        'address': ns.get('school_address',''),
                        'distance': ns.get('distance',''),
                        'attributes': {
                            'type': ns.get('school_type',''),
                            'sector': ns.get('school_sector',''),
                            'gender': ns.get('school_gender',''),
                            'year_levels': ns.get('year_levels',''),
                            'enrollments': ns.get('enrollments','')
                        }
                    }
                    if (ns.get('catchment_status') or '').lower() == 'in catchment'.lower():
                        in_catch.append(school_obj)
                    else:
                        all_near.append(school_obj)
                raw['Nearby_Schools_In_Catchment'] = json.dumps(in_catch)
                raw['Nearby_Schools_All_Nearby'] = json.dumps(all_near)
                
                # Property history data (already sorted by ORDER BY event_date DESC in query)
                history_events = []
                for ph in ph_rows:
                    event = {
                        'date': ph.get('event_date', ''),
                        'description': ph.get('event_description', ''),
                        'details': ph.get('event_details', ''),
                        'type': ph.get('history_type', '').lower()
                    }
                    history_events.append(event)
                
                if history_events:
                    # Create events by type
                    events_by_type = {
                        'sale': [e for e in history_events if e['type'] == 'sale'],
                        'rental': [e for e in history_events if e['type'] == 'rental'],
                        'listing': [e for e in history_events if e['type'] == 'listing'],
                        'da': [e for e in history_events if e['type'] == 'da'],
                        'other': [e for e in history_events if e['type'] not in ['sale', 'rental', 'listing', 'da']]
                    }
                    
                    # Calculate total unique events
                    total_events = len(history_events)
                    
                    # Debug each category
                    logger.info(f"🔍 Total history events: {total_events}")
                    for category, events in events_by_type.items():
                        logger.info(f"🔍 {category} category has {len(events)} events")
                        for event in events:
                            logger.info(f"🔍   - {event['date']}: {event['description']} (type: {event['type']})")
                    
                    history_data = {
                        'events_by_type': events_by_type,
                        'total_events': total_events
                    }
                    raw['Property_History_All'] = json.dumps(history_data)
                else:
                    logger.info("🔍 No history events found in database")

                logger.info(f"🔍 Raw household data: Owner_Type='{raw.get('Owner_Type')}', Current_Tenure='{raw.get('Current_Tenure')}', Owner_Info='{raw.get('Household_Information_Owner_Information')}', Marketing_Contacts='{raw.get('Household_Information_Marketing_Contacts')}'")
                
                api_data = _transform_for_api(raw)
                return {
                    'success': True,
                    'message': 'Property data loaded from database',
                    'data': api_data
                }
    except Exception as e:
        logger.error(f"⚠️ Pre-check DB lookup failed: {e}")
        # Continue to scraping path

    max_attempts = 3
    for attempt in range(max_attempts):
        logger.info(f"🔁 Attempt {attempt+1}/{max_attempts}")
        # Setup Chrome driver (fresh per attempt; headless, incognito, no prior sessions)
        options = Options()
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--incognito')
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(600)
        driver.set_script_timeout(600)
        
        try:
            # Step 1: Login
            logger.info("🔐 Starting login process...")
            driver.get("https://rpp.corelogic.com.au/")
            logger.info("✅ Login page loaded")
        
            # Always perform fresh login
            time.sleep(2)
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
            time.sleep(6)
            current_url = driver.current_url
            logger.info(f"URL after login attempt: {current_url}")
                
        except Exception as login_error:
            logger.error(f"⚠️ Could not login: {login_error}")        
        
        
        # Wait for main page to fully load before proceeding
        logger.info("⏳ Waiting for main page to load completely...")
        time.sleep(10)
        
        # Step 2: Click the burger menu (COMMENTED OUT - using direct search instead)
        # logger.info("🍔 Clicking burger menu...")
        # try:
        #     # Wait for the burger menu to be present and clickable
        #     burger_menu = WebDriverWait(driver, 20).until(
        #         EC.element_to_be_clickable((By.CSS_SELECTOR, "button.rpd-burger-menu"))
        #     )
        #     burger_menu.click()
        #     logger.info("✅ Burger menu clicked")
        #     time.sleep(2)  # Wait for menu to open
        # except Exception as e:
        #     logger.error(f"❌ Failed to click burger menu: {e}")
        #     last_error = e
        #     driver.quit()
        #     # Retry next attempt
        #     time.sleep(2 * (attempt + 1))
        #     continue
        
        # Step 2: Wait for search bar to be available and enter address directly
        logger.info(f"🔍 Waiting for search bar to be enabled and entering address: {address}")
        try:
            # Wait for search input to be present, visible, and enabled
            search_input = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "crux-multi-locality-search"))
            )
            
            # Additional check to ensure the search bar is actually enabled/not disabled
            max_wait_attempts = 10
            wait_attempt = 0
            while wait_attempt < max_wait_attempts:
                if search_input.is_enabled() and search_input.is_displayed():
                    logger.info("✅ Search bar is enabled and ready")
                    break
                else:
                    logger.info(f"⏳ Search bar not ready yet, waiting... (attempt {wait_attempt + 1}/{max_wait_attempts})")
                    time.sleep(2)
                    wait_attempt += 1
                    # Re-find the element in case it changed
                    search_input = driver.find_element(By.ID, "crux-multi-locality-search")
            
            if wait_attempt >= max_wait_attempts:
                logger.warning("⚠️ Search bar may not be fully enabled, proceeding anyway...")
            
            # Clear any existing text and enter the address
            search_input.clear()
            time.sleep(0.5)  # Brief pause after clearing
            search_input.send_keys(address)
            logger.info("✅ Address entered in search bar")
            
            # Wait a moment to see if dropdown appears automatically
            time.sleep(3)
            
            # Check if dropdown options are already visible
            try:
                dropdown_options = driver.find_elements(By.CSS_SELECTOR, ".MuiAutocomplete-option, [role='option']")
                if not dropdown_options:
                    # If no dropdown options visible, click search bar to make dropdown appear
                    search_input.click()
                    logger.info("✅ Clicked search bar to show dropdown")
                    time.sleep(3)
                else:
                    logger.info("✅ Dropdown appeared automatically")
            except:
                # If we can't check, click search bar as fallback
                search_input.click()
                logger.info("✅ Clicked search bar as fallback")
                time.sleep(3)
                
        except Exception as e:
            logger.error(f"❌ Failed to enter address in search bar: {e}")
            last_error = e
            driver.quit()
            time.sleep(2 * (attempt + 1))
            continue
        
        # Step 3: Check if dropdown options are available, then validate and click
        logger.info("📋 Checking for dropdown options...")
        try:
            # First, check if any dropdown options are available
            dropdown_options = driver.find_elements(By.CSS_SELECTOR, ".MuiAutocomplete-option, [role='option']")
            
            if not dropdown_options:
                logger.warning("⚠️ No dropdown options found - address may not exist in database")
                driver.quit()
                return {
                    'success': False,
                    'message': 'Address not found. Please check the address and try again.',
                    'data': None
                }
            
            logger.info(f"✅ Found {len(dropdown_options)} dropdown options")
            
            # Wait for dropdown options to appear and get the first one
            try:
                first_option = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".MuiAutocomplete-option:first-child, [role='option']:first-child"))
                )
            except TimeoutException:
                logger.warning("⚠️ Timeout waiting for dropdown options - address may not exist")
                driver.quit()
                return {
                    'success': False,
                    'message': 'Address not found. Please check the address and try again.',
                    'data': None
                }

            # Get visible text for similarity check
            option_text = first_option.text.strip()
            input_text = address.strip()

            # Normalize by lowering case and collapsing whitespace
            def _norm(s: str) -> str:
                return re.sub(r"\s+", " ", s.lower()).strip()

            ratio = difflib.SequenceMatcher(None, _norm(input_text), _norm(option_text)).ratio()
            logger.info(f"🔎 First option similarity: {ratio:.3f} | option='{option_text[:120]}'")

            if ratio < 0.90:
                logger.error("❌ First dropdown option is not a close enough match to input address")
                driver.quit()
                return {
                    'success': False,
                    'message': f"Top suggestion didn't match input sufficiently (similarity={ratio:.2f}).",
                    'data': None
                }

            # Click the validated first option
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".MuiAutocomplete-option:first-child, [role='option']:first-child"))).click()
            logger.info("✅ First dropdown option clicked (similarity >= 0.90)")
            time.sleep(2)  # Wait for selection
        except Exception as e:
            logger.error(f"❌ Failed during dropdown validation/click: {e}")
            last_error = e
            driver.quit()
            time.sleep(2 * (attempt + 1))
            continue
        
        # Step 4: Wait for results page to load (search happens automatically after dropdown selection)
        logger.info("⏳ Waiting for results page to load...")
        time.sleep(8)
        
        # Step 5.5: Check for "Results for '{address}'" message indicating incomplete address
        logger.info("🔍 Checking for incomplete address indicators...")
        try:
            # Get the entire page text to check for "Results for" patterns
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            logger.info(f"🔍 Page text sample (first 500 chars): {page_text[:500]}")
            
            # Check for various "Results for" patterns
            results_patterns = [
                "results for",
                "results for '",
                "results for \"",
                "search results for",
                "multiple results for"
            ]
            
            for pattern in results_patterns:
                if pattern in page_text:
                    logger.warning(f"⚠️ Found 'Results for' pattern in page: '{pattern}'")
                    logger.warning(f"⚠️ Full page text containing pattern: {page_text}")
                    driver.quit()
                    return {
                        'success': False,
                        'message': 'Please write complete and accurate address',
                        'data': None
                    }
            
            # Also check specific elements that might contain this text
            results_indicators = [
                "//h4[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'results for')]",
                "//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'results for')]",
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'results for')]",
                "//h4[contains(translate(@title, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'results for')]"
            ]
            time.sleep(8)
            # Special check for h4 elements with title attributes (common pattern)
            try:
                h4_elements = driver.find_elements(By.TAG_NAME, "h4")
                logger.info(f"🔍 Found {len(h4_elements)} h4 elements on page")
                for h4 in h4_elements:
                    title_attr = h4.get_attribute('title') or ""
                    text_content = h4.text or ""
                    logger.info(f"🔍 H4 element - text: '{text_content}', title: '{title_attr}'")
                    
                    if "results for" in title_attr.lower() or "results for" in text_content.lower():
                        logger.warning(f"⚠️ Found 'Results for' in h4 element - text: '{text_content}', title: '{title_attr}'")
                        driver.quit()
                        return {
                            'success': False,
                            'message': 'Please write complete and accurate address',
                            'data': None
                        }
            except Exception as e:
                logger.warning(f"⚠️ Error checking h4 elements: {e}")
            
            for indicator in results_indicators:
                try:
                    result_elements = driver.find_elements(By.XPATH, indicator)
                    for result_element in result_elements:
                        if result_element:
                            # Check both text content and title attribute
                            result_text = (result_element.text or "").lower()
                            result_title = (result_element.get_attribute('title') or "").lower()
                            
                            logger.info(f"🔍 Checking element - text: '{result_text}', title: '{result_title}'")
                            
                            if "results for" in result_text or "results for" in result_title:
                                logger.warning(f"⚠️ Found 'Results for' indicator - text: '{result_text}', title: '{result_title}'")
                                driver.quit()
                                return {
                                    'success': False,
                                    'message': 'Please write complete and accurate address',
                                    'data': None
                                }
                except Exception as e:
                    logger.warning(f"⚠️ Error checking element: {e}")
                    continue
                    
            logger.info("✅ No 'Results for' indicators found - proceeding with extraction")
        except Exception as e:
            logger.warning(f"⚠️ Error checking for 'Results for' indicators: {e}")
            # Continue with extraction even if check fails
        
        # Step 5: Wait for "Property Notes" H4 element to ensure page is fully loaded
        logger.info("⏳ Waiting for 'Property Notes' H4 element to appear...")
        try:
            # Wait for the H4 element with "Property Notes" text
            property_notes_h4 = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//h4[contains(text(), 'Property Notes')]"))
            )
            logger.info("✅ 'Property Notes' H4 element found - page is fully loaded")
            time.sleep(2)  # Additional brief wait to ensure everything is ready
        except TimeoutException:
            logger.warning("⚠️ 'Property Notes' H4 element not found within 30 seconds, proceeding anyway...")
        except Exception as e:
            logger.warning(f"⚠️ Error waiting for 'Property Notes' H4 element: {e}, proceeding anyway...")
        
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
                
                # Step 8: Retrieve data from database (same flow as existing properties)
                logger.info("🔄 Retrieving data from database to ensure consistency...")
                try:
                    connection = psycopg2.connect(os.getenv('DATABASE_URL'))
                    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                        # Fetch complete property data for the stored property
                        cursor.execute("SELECT * FROM properties WHERE id = %s", (property_id,))
                        best = cursor.fetchone()
                        
                        if best:
                            # Fetch related data for transformation (same as existing property flow)
                            # sale_rental_info
                            cursor.execute("SELECT * FROM sale_rental_info WHERE property_id = %s LIMIT 1", (property_id,))
                            sri = cursor.fetchone() or {}
                            # additional_info
                            cursor.execute("SELECT * FROM additional_info WHERE property_id = %s LIMIT 1", (property_id,))
                            ai = cursor.fetchone() or {}
                            # household_info
                            cursor.execute("SELECT * FROM household_info WHERE property_id = %s LIMIT 1", (property_id,))
                            hi = cursor.fetchone() or {}
                            # valuation_estimates
                            cursor.execute("SELECT * FROM valuation_estimates WHERE property_id = %s", (property_id,))
                            ve_rows = cursor.fetchall() or []
                            # nearby_schools
                            cursor.execute("SELECT * FROM nearby_schools WHERE property_id = %s", (property_id,))
                            ns_rows = cursor.fetchall() or []
                            # property_attributes
                            cursor.execute("SELECT * FROM property_attributes WHERE property_id = %s LIMIT 1", (property_id,))
                            pa = cursor.fetchone() or {}
                            # property_history
                            cursor.execute("SELECT * FROM property_history WHERE property_id = %s ORDER BY event_date DESC", (property_id,))
                            ph_rows = cursor.fetchall() or []

                            # Construct raw-like dict for _transform_for_api (same as existing property flow)
                            raw = {
                                'id': property_id,
                                'Property_URL': best.get('property_url',''),
                                'Address': best.get('address',''),
                                'Property_Type': best.get('property_type',''),
                                'Bedrooms': best.get('bedrooms',''),
                                'Bathrooms': best.get('bathrooms',''),
                                'Car_Spaces': best.get('car_spaces',''),
                                'Land_Size': best.get('land_size',''),
                                'Floor_Area': best.get('floor_area',''),
                                'Last_Sold_Price': sri.get('last_sold_price',''),
                                'Last_Sold_Date': sri.get('last_sold_date',''),
                                'Sold_By': sri.get('sold_by',''),
                                'Land_Use': sri.get('land_use',''),
                                'Issue_Date': sri.get('issue_date',''),
                                'Advertisement_Date': sri.get('advertisement_date',''),
                                'Listing_Description': sri.get('listing_description',''),
                                'Advertising_Agency': sri.get('advertising_agency',''),
                                'Advertising_Agent': sri.get('advertising_agent',''),
                                'Agent_Phone': sri.get('agent_phone',''),
                                'Additional_Information_Legal_Description': ai.get('legal_description',''),
                                'Additional_Information_Property_Features': ai.get('property_features',''),
                                'Additional_Information_Land_Values': ai.get('land_values',''),
                                'Owner_Type': hi.get('owner_type',''),
                                'Current_Tenure': hi.get('current_tenure',''),
                                'Household_Information_Owner_Information': hi.get('owner_information',''),
                                'Household_Information_Marketing_Contacts': hi.get('marketing_contacts',''),
                                'Valuation_Estimate_Estimate': '',
                                'Valuation_Estimate_Estimate_JSON': '',
                                'Valuation_Estimate_Rental': '',
                                'Valuation_Estimate_Rental_JSON': '',
                                'Nearby_Schools_In_Catchment': '[]',
                                'Nearby_Schools_All_Nearby': '[]',
                                'Property_Attributes_JSON': pa.get('attributes_json','{}'),
                                'Property_History_All': '[]',
                                'Scraping_Date': time.strftime('%Y-%m-%d %H:%M:%S')
                            }
                            
                            # Populate valuation details
                            for ve in ve_rows:
                                if (ve.get('estimate_type') or '').lower() == 'property valuation':
                                    raw['Valuation_Estimate_Estimate_JSON'] = json.dumps({
                                        'confidence': ve.get('confidence_level',''),
                                        'low_value': ve.get('low_value',''),
                                        'mid_value': ve.get('mid_value',''),
                                        'high_value': ve.get('high_value','')
                                    })
                                elif (ve.get('estimate_type') or '').lower() == 'rental estimate':
                                    raw['Valuation_Estimate_Rental_JSON'] = json.dumps({
                                        'confidence': ve.get('confidence_level',''),
                                        'low_value': ve.get('low_value',''),
                                        'mid_value': ve.get('mid_value',''),
                                        'high_value': ve.get('high_value','')
                                    })
                            
                            # Populate schools data
                            in_catch = []
                            all_near = []
                            for ns in ns_rows:
                                school_obj = {
                                    'name': ns.get('school_name',''),
                                    'address': ns.get('school_address',''),
                                    'distance': ns.get('distance',''),
                                    'attributes': {
                                        'type': ns.get('school_type',''),
                                        'sector': ns.get('school_sector',''),
                                        'gender': ns.get('school_gender',''),
                                        'year_levels': ns.get('year_levels',''),
                                        'enrollments': ns.get('enrollments','')
                                    }
                                }
                                if (ns.get('catchment_status') or '').lower() == 'in catchment'.lower():
                                    in_catch.append(school_obj)
                                else:
                                    all_near.append(school_obj)
                            raw['Nearby_Schools_In_Catchment'] = json.dumps(in_catch)
                            raw['Nearby_Schools_All_Nearby'] = json.dumps(all_near)
                            
                            # Property history data (already sorted by ORDER BY event_date DESC in query)
                            history_events = []
                            for ph in ph_rows:
                                event = {
                                    'date': ph.get('event_date', ''),
                                    'description': ph.get('event_description', ''),
                                    'details': ph.get('event_details', ''),
                                    'type': ph.get('history_type', '').lower()
                                }
                                history_events.append(event)
                            
                            if history_events:
                                # Create events by type
                                events_by_type = {
                                    'sale': [e for e in history_events if e['type'] == 'sale'],
                                    'rental': [e for e in history_events if e['type'] == 'rental'],
                                    'listing': [e for e in history_events if e['type'] == 'listing'],
                                    'da': [e for e in history_events if e['type'] == 'da'],
                                    'other': [e for e in history_events if e['type'] not in ['sale', 'rental', 'listing', 'da']]
                                }
                                
                                # Calculate total unique events
                                total_events = len(history_events)
                                
                                # Debug each category
                                logger.info(f"🔍 Retrieved from DB - Total history events: {total_events}")
                                for category, events in events_by_type.items():
                                    logger.info(f"🔍 Retrieved from DB - {category} category has {len(events)} events")
                                    for event in events:
                                        logger.info(f"🔍 Retrieved from DB - {event['date']}: {event['description']} (type: {event['type']})")
                                
                                history_data = {
                                    'events_by_type': events_by_type,
                                    'total_events': total_events
                                }
                                raw['Property_History_All'] = json.dumps(history_data)
                            else:
                                logger.info("🔍 Retrieved from DB - No history events found")

                            logger.info(f"🔍 Retrieved from DB - Raw household data: Owner_Type='{raw.get('Owner_Type')}', Current_Tenure='{raw.get('Current_Tenure')}', Owner_Info='{raw.get('Household_Information_Owner_Information')}', Marketing_Contacts='{raw.get('Household_Information_Marketing_Contacts')}'")
                            
                            api_data = _transform_for_api(raw)
                            driver.quit()
                            return {
                                'success': True,
                                'message': 'Property data scraped, saved, and retrieved from database successfully',
                                'data': api_data
                            }
                        else:
                            logger.error("❌ Failed to retrieve property from database after saving")
                            last_error = Exception('Failed to retrieve property from database after saving')
                            driver.quit()
                            time.sleep(2 * (attempt + 1))
                            continue
                except Exception as e:
                    logger.error(f"❌ Error retrieving data from database: {e}")
                    last_error = e
                    driver.quit()
                    time.sleep(2 * (attempt + 1))
                    continue
            else:
                logger.error("❌ Failed to store property in database")
                last_error = Exception('Failed to store property in database')
                driver.quit()
                time.sleep(2 * (attempt + 1))
                continue
        else:
            logger.error("❌ Failed to extract property data")
            last_error = Exception('Failed to extract property data')
            driver.quit()
            time.sleep(2 * (attempt + 1))
            continue
        
    # All attempts failed
    return {
        'success': False,
        'message': f'Error during scraping after {max_attempts} attempts: {str(last_error) if last_error else "Unknown error"}',
        'data': None
    }

# Example usage
if __name__ == "__main__":
    import sys
    
    # Check if address is provided as command line argument
    if len(sys.argv) > 1:
        address = sys.argv[1]
    else:
        address = "1 Macquarie Street Sydney NSW 2000"  # Default test address
    
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

