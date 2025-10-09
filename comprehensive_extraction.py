
import time
import json
import re
import logging
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException

# Configure logging
logger = logging.getLogger(__name__)

def safe_get_text(driver, by, value, default=""):
    """Safely get text from an element, return default if not found."""
    try:
        element = driver.find_element(by, value)
        return element.text.strip()
    except (NoSuchElementException, ElementClickInterceptedException):
        return default

def extract_comprehensive_property_data(driver, url):
    """Extract comprehensive property data from the current page using all available tabs and sections."""
    logger.info(f"🔍 Extracting comprehensive property data from: {url}")
    
    try:
        # Initialize comprehensive property data structure
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
            'Properties_Sold_12_Months': '',
            'Property_History_All': '',
            'Property_History_Sale': '',
            'Property_History_Listing': '',
            'Property_History_Rental': '',
            'Property_History_DA': '',
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
            
            'Scraping_Date': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Wait for page to fully load
        time.sleep(3)
        
        # Extract basic property information
        try:
            # Extract address
            address = safe_get_text(driver, By.ID, "attr-single-line-address")
            if not address:
                address_selectors = ["h1", ".property-address", "[data-testid='property-address']", ".address"]
                for selector in address_selectors:
                    address = safe_get_text(driver, By.CSS_SELECTOR, selector)
                    if address:
                        break
            
            # Clean up address - remove "Copy" suffix if present
            if address and address.endswith("Copy"):
                address = address[:-4].strip()
            
            property_data['Address'] = address
            logger.info(f"  ✅ Address extracted: {address}")
        except Exception as e:
            logger.error(f"  ❌ Address extraction failed: {e}")
        
        # Extract property attributes
        property_attributes = {}
        
        # Bedrooms
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
        except:
            property_data['Bedrooms'] = '-'
            property_attributes['bedrooms'] = '-'
            
        # Bathrooms
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
            
        # Car Spaces
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
            
        # Land Size
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
            
        # Floor Area
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
        
        # Extract sale information
        try:
            sale_data = {}
            sale_price_elem = driver.find_element(By.CSS_SELECTOR, '.sale-price')
            sale_text = sale_price_elem.text.strip()
            price_match = re.search(r'\$([0-9,]+)', sale_text)
            date_match = re.search(r'(\d{1,2} \w+ \d{4})', sale_text)
            
            if price_match:
                sale_data['price'] = price_match.group(1).replace(',', '')
                property_data['Last_Sold_Price'] = price_match.group(1).replace(',', '')
            if date_match:
                sale_data['date'] = date_match.group(1)
                property_data['Last_Sold_Date'] = date_match.group(1)
            
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
            
        try:
            advertisement_date = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="sale-detail-advertisement-date"] .property-attribute-val')
            property_data['Advertisement_Date'] = advertisement_date
        except:
            pass
        
        # Extract listing description and advertising information
        try:
            # Extract advertisement date
            try:
                ad_date_elem = driver.find_element(By.CSS_SELECTOR, '[data-testid="advertisement-date"] .attr-value')
                property_data['Advertisement_Date'] = ad_date_elem.text.strip()
            except:
                property_data['Advertisement_Date'] = ''
            
            # Extract listing description
            try:
                desc_elem = driver.find_element(By.CSS_SELECTOR, '[data-testid="listing-desc"]')
                property_data['Listing_Description'] = desc_elem.text.strip()
            except:
                property_data['Listing_Description'] = ''
            
            # Extract advertising agent information (multiple agents)
            try:
                agents_data = []
                
                # First, try to click "Show More" link to reveal advertising agent information
                try:
                    show_more_link = driver.find_element(By.CSS_SELECTOR, '[data-testid="listing-description-panel"] a[href="#"]')
                    if show_more_link and show_more_link.is_displayed():
                        if "Show More" in show_more_link.text:
                            logger.info("  🔍 Clicking 'Show More' to reveal advertising agent information")
                            driver.execute_script("arguments[0].click();", show_more_link)
                            time.sleep(2)  # Wait for content to load
                        elif "Show Less" in show_more_link.text:
                            logger.info("  ℹ️ 'Show Less' link found - content already expanded")
                    else:
                        logger.info("  ℹ️ No 'Show More' link found - content may already be expanded")
                except Exception as show_more_error:
                    logger.info(f"  ℹ️ Could not find or click 'Show More' link: {show_more_error}")
                
                # Find all advertiser lists
                advertiser_lists = driver.find_elements(By.CSS_SELECTOR, '[data-testid="listing-description-panel"] .advertiser-list')
                logger.info(f"  🔍 Found {len(advertiser_lists)} advertiser lists")
                
                for i, advertiser_list in enumerate(advertiser_lists):
                    try:
                        agent_info = {}
                        logger.info(f"  🔍 Processing advertiser list {i+1}")
                        
                        # Extract agency - try multiple approaches
                        try:
                            # Method 1: Look for the specific structure (attr-value is sibling, not following-sibling)
                            agency_elem = advertiser_list.find_element(By.XPATH, './/span[@class="attr-label" and contains(text(), "Advertising Agency")]/../span[@class="attr-value"]')
                            agent_info['advertising_agency'] = agency_elem.text.strip()
                            logger.info(f"    ✅ Agency found: {agent_info['advertising_agency']}")
                        except:
                            # Method 2: Look for any span with "Advertising Agency" text
                            try:
                                agency_spans = advertiser_list.find_elements(By.XPATH, './/span[contains(text(), "Advertising Agency")]')
                                for span in agency_spans:
                                    try:
                                        # Get the parent p element, then find the attr-value span
                                        parent_p = span.find_element(By.XPATH, '..')
                                        value_span = parent_p.find_element(By.XPATH, './/span[@class="attr-value"]')
                                        agent_info['advertising_agency'] = value_span.text.strip()
                                        logger.info(f"    ✅ Agency found (method 2): {agent_info['advertising_agency']}")
                                        break
                                    except:
                                        continue
                            except:
                                pass
                        
                        # Extract agent name
                        try:
                            agent_elem = advertiser_list.find_element(By.XPATH, './/span[@class="attr-label" and contains(text(), "Advertising Agent")]/../span[@class="attr-value"]')
                            agent_info['advertising_agent'] = agent_elem.text.strip()
                            logger.info(f"    ✅ Agent found: {agent_info['advertising_agent']}")
                        except:
                            try:
                                agent_spans = advertiser_list.find_elements(By.XPATH, './/span[contains(text(), "Advertising Agent")]')
                                for span in agent_spans:
                                    try:
                                        # Get the parent p element, then find the attr-value span
                                        parent_p = span.find_element(By.XPATH, '..')
                                        value_span = parent_p.find_element(By.XPATH, './/span[@class="attr-value"]')
                                        agent_info['advertising_agent'] = value_span.text.strip()
                                        logger.info(f"    ✅ Agent found (method 2): {agent_info['advertising_agent']}")
                                        break
                                    except:
                                        continue
                            except:
                                pass
                        
                        # Extract phone number
                        try:
                            phone_elem = advertiser_list.find_element(By.XPATH, './/span[@class="attr-label" and contains(text(), "Agent Phone Number")]/../span[@class="attr-value"]')
                            agent_info['agent_phone'] = phone_elem.text.strip()
                            logger.info(f"    ✅ Phone found: {agent_info['agent_phone']}")
                        except:
                            try:
                                phone_spans = advertiser_list.find_elements(By.XPATH, './/span[contains(text(), "Agent Phone Number")]')
                                for span in phone_spans:
                                    try:
                                        # Get the parent p element, then find the attr-value span
                                        parent_p = span.find_element(By.XPATH, '..')
                                        value_span = parent_p.find_element(By.XPATH, './/span[@class="attr-value"]')
                                        agent_info['agent_phone'] = value_span.text.strip()
                                        logger.info(f"    ✅ Phone found (method 2): {agent_info['agent_phone']}")
                                        break
                                    except:
                                        continue
                            except:
                                pass
                        
                        if agent_info:
                            agents_data.append(agent_info)
                            logger.info(f"    ✅ Agent info added: {agent_info}")
                        else:
                            logger.warning(f"    ⚠️ No agent info found in advertiser list {i+1}")
                            
                    except Exception as agent_error:
                        logger.error(f"  ⚠️ Error extracting agent info from list {i+1}: {agent_error}")
                        continue
                
                # Store agents data as JSON
                if agents_data:
                    property_data['Advertising_Agent_Info_JSON'] = json.dumps(agents_data)
                    logger.info(f"  ✅ Stored {len(agents_data)} agents in JSON")
                    
                    # Also store first agent info in individual fields for backward compatibility
                    if len(agents_data) > 0:
                        first_agent = agents_data[0]
                        property_data['Advertising_Agency'] = first_agent.get('advertising_agency', '')
                        property_data['Advertising_Agent'] = first_agent.get('advertising_agent', '')
                        property_data['Agent_Phone'] = first_agent.get('agent_phone', '')
                        logger.info(f"  ✅ First agent stored: {first_agent}")
                else:
                    logger.warning(f"  ⚠️ No advertising agent data found")
                
            except Exception as e:
                logger.error(f"  ⚠️ Error extracting advertising agent information: {e}")
                
        except Exception as e:
            logger.error(f"  ⚠️ Error extracting listing description: {e}")
        
        
        
        # Extract Additional Information - Legal Description, Property Features, Land Values (using sales_scraping.py method)
        try:
            additional_tabs = {
                'Legal Description': 'Additional_Information_Legal_Description',
                'Property Features': 'Additional_Information_Property_Features',
                'Land Values': 'Additional_Information_Land_Values'
            }
            
            for tab_name, column_name in additional_tabs.items():
                try:
                    # Try to click on the specific tab
                    tab_element = driver.find_element(By.CSS_SELECTOR, f'[data-testid="crux-tab-menu-{tab_name}"]')
                    if tab_element and tab_element.is_enabled():
                        driver.execute_script("arguments[0].click();", tab_element)
                        time.sleep(3)  # Wait for content to load
                        
                        # Extract structured data based on tab type
                        if tab_name == 'Legal Description':
                            # Extract legal description data
                            legal_data = {}
                            
                            # Get all legal description rows
                            legal_rows = driver.find_elements(By.CSS_SELECTOR, '#legal-description .legal-desc-row')
                            
                            for row in legal_rows:
                                try:
                                    label_elem = row.find_element(By.CSS_SELECTOR, '.flex-label p')
                                    content_elem = row.find_element(By.CSS_SELECTOR, '.flex-content p')
                                    
                                    label = label_elem.text.strip()
                                    content = content_elem.text.strip()
                                    
                                    # Clean up content (remove tooltip icons, etc.)
                                    if 'Withheld' in content:
                                        content = 'Withheld'
                                    
                                    if label and content:
                                        legal_data[label] = content
                                        
                                except Exception as row_error:
                                    logger.error(f"  ⚠️ Error extracting legal row: {row_error}")
                                    continue
                            
                            content = json.dumps(legal_data) if legal_data else "{}"
                            
                        elif tab_name == 'Property Features':
                            # Extract property features data
                            features_data = {}
                            
                            # Try multiple selectors for property features
                            feature_selectors = [
                                '#property-features .flex-container',
                                '#property-features .legal-desc-row', 
                                '#property-features .flex-label',
                                '.tab-content .flex-container',
                                '.tab-content .legal-desc-row'
                            ]
                            
                            feature_rows = []
                            for selector in feature_selectors:
                                try:
                                    rows = driver.find_elements(By.CSS_SELECTOR, selector)
                                    if rows:
                                        feature_rows = rows
                                        logger.info(f"  🔍 Found {len(rows)} feature rows with selector: {selector}")
                                        break
                                except:
                                    continue
                            
                            if not feature_rows:
                                # Fallback: try to get any key-value pairs in the current tab content
                                try:
                                    # Look for any elements that might contain property features
                                    all_elements = driver.find_elements(By.CSS_SELECTOR, '.tab-content *')
                                    for elem in all_elements:
                                        try:
                                            text = elem.text.strip()
                                            if text and ':' in text:
                                                parts = text.split(':', 1)
                                                if len(parts) == 2:
                                                    key = parts[0].strip()
                                                    value = parts[1].strip()
                                                    if key and value:
                                                        features_data[key] = value
                                        except:
                                            continue
                                except Exception as fallback_error:
                                    logger.error(f"  ⚠️ Fallback extraction failed: {fallback_error}")
                            
                            for row in feature_rows:
                                try:
                                    # Try multiple selectors for label and content
                                    label_selectors = ['.flex-label p', '.flex-label', 'p:first-child', '.label']
                                    content_selectors = ['.flex-content p', '.flex-content', 'p:last-child', '.value', '.content']
                                    
                                    label = ""
                                    content = ""
                                    
                                    for label_sel in label_selectors:
                                        try:
                                            label_elem = row.find_element(By.CSS_SELECTOR, label_sel)
                                            label = label_elem.text.strip()
                                            if label:
                                                break
                                        except:
                                            continue
                                    
                                    for content_sel in content_selectors:
                                        try:
                                            content_elem = row.find_element(By.CSS_SELECTOR, content_sel)
                                            content = content_elem.text.strip()
                                            if content:
                                                break
                                        except:
                                            continue
                                    
                                    if label and content:
                                        features_data[label] = content
                                        
                                except Exception as row_error:
                                    logger.error(f"  ⚠️ Error extracting feature row: {row_error}")
                                    continue
                            
                            content = json.dumps(features_data) if features_data else "{}"
                            
                        elif tab_name == 'Land Values':
                            # Extract land values data
                            values_data = {}
                            
                            # Try multiple selectors for land values
                            value_selectors = [
                                '#land-values .flex-container',
                                '#land-values .legal-desc-row',
                                '#land-values .flex-label',
                                '.tab-content .flex-container',
                                '.tab-content .legal-desc-row'
                            ]
                            
                            value_rows = []
                            for selector in value_selectors:
                                try:
                                    rows = driver.find_elements(By.CSS_SELECTOR, selector)
                                    if rows:
                                        value_rows = rows
                                        logger.info(f"  🔍 Found {len(rows)} value rows with selector: {selector}")
                                        break
                                except:
                                    continue
                            
                            if not value_rows:
                                # Fallback: try to get any key-value pairs in the current tab content
                                try:
                                    # Look for any elements that might contain land values
                                    all_elements = driver.find_elements(By.CSS_SELECTOR, '.tab-content *')
                                    for elem in all_elements:
                                        try:
                                            text = elem.text.strip()
                                            if text and ':' in text:
                                                parts = text.split(':', 1)
                                                if len(parts) == 2:
                                                    key = parts[0].strip()
                                                    value = parts[1].strip()
                                                    if key and value:
                                                        values_data[key] = value
                                        except:
                                            continue
                                except Exception as fallback_error:
                                    logger.error(f"  ⚠️ Fallback extraction failed: {fallback_error}")
                            
                            for row in value_rows:
                                try:
                                    # Try multiple selectors for label and content
                                    label_selectors = ['.flex-label p', '.flex-label', 'p:first-child', '.label']
                                    content_selectors = ['.flex-content p', '.flex-content', 'p:last-child', '.value', '.content']
                                    
                                    label = ""
                                    content = ""
                                    
                                    for label_sel in label_selectors:
                                        try:
                                            label_elem = row.find_element(By.CSS_SELECTOR, label_sel)
                                            label = label_elem.text.strip()
                                            if label:
                                                break
                                        except:
                                            continue
                                    
                                    for content_sel in content_selectors:
                                        try:
                                            content_elem = row.find_element(By.CSS_SELECTOR, content_sel)
                                            content = content_elem.text.strip()
                                            if content:
                                                break
                                        except:
                                            continue
                                    
                                    if label and content:
                                        values_data[label] = content
                                        
                                except Exception as row_error:
                                    logger.error(f"  ⚠️ Error extracting value row: {row_error}")
                                    continue
                            
                            content = json.dumps(values_data) if values_data else "{}"
                        
                        property_data[column_name] = content if content != "{}" else 'Not available'
                        logger.info(f"  ✅ {tab_name} extracted: {len(content)} characters")
                    else:
                        property_data[column_name] = 'Tab not available'
                        logger.warning(f"  ⚠️ {tab_name} tab not available")
                except Exception as e:
                    property_data[column_name] = 'Not available'
                    logger.error(f"  ❌ {tab_name} extraction failed: {e}")
        except Exception as e:
            logger.error(f"  ❌ Additional information extraction failed: {e}")
        
        # Extract Household Information
        try:
            # Initialize individual fields
            property_data['Owner_Name'] = ''
            property_data['Current_Tenure'] = ''
            property_data['Owner_Type'] = ''
            property_data['Marketing_Contacts_JSON'] = json.dumps([])
            
            household_tabs = {
                'Owner Information': 'Household_Information_Owner_Information',
                'Marketing Contacts': 'Household_Information_Marketing_Contacts'
            }
            
            for tab_name, column_name in household_tabs.items():
                try:
                    tab_element = driver.find_element(By.CSS_SELECTOR, f'[data-testid="crux-tab-menu-{tab_name}"]')
                    if tab_element and tab_element.is_enabled():
                        driver.execute_script("arguments[0].click();", tab_element)
                        time.sleep(2)
                        
                        # Extract structured household information
                        household_data = {}
                        
                        if tab_name == 'Owner Information':
                            # Extract owner information fields
                            try:
                                # Extract Name - look for the span containing "Withheld" or actual name
                                try:
                                    name_elem = driver.find_element(By.CSS_SELECTOR, '.owner-name-label + span span')
                                    name_text = name_elem.text.strip()
                                    if name_text:
                                        household_data['Name'] = name_text
                                except:
                                    # Fallback: look for any span after the name label
                                    try:
                                        name_elem = driver.find_element(By.CSS_SELECTOR, '.owner-name-label')
                                        # Get the next sibling span that contains the name
                                        name_span = name_elem.find_element(By.XPATH, 'following-sibling::span//span')
                                        name_text = name_span.text.strip()
                                        if name_text:
                                            household_data['Name'] = name_text
                                    except:
                                        pass
                                
                                # Extract Current Tenure - look for the tenure text
                                try:
                                    tenure_elem = driver.find_element(By.CSS_SELECTOR, '.tenure')
                                    tenure_text = tenure_elem.text.strip()
                                    if tenure_text:
                                        household_data['Current Tenure'] = tenure_text
                                except:
                                    pass
                                
                                # Extract Owner Type - look for the owner-type class
                                try:
                                    owner_type_elem = driver.find_element(By.CSS_SELECTOR, '.owner-type')
                                    owner_type_text = owner_type_elem.text.strip()
                                    if owner_type_text:
                                        household_data['Owner Type'] = owner_type_text
                                except:
                                    pass
                                
                            except Exception as e:
                                logger.error(f"  ⚠️ Error extracting owner information: {e}")
                        
                        elif tab_name == 'Marketing Contacts':
                            # Extract marketing contacts
                            try:
                                # Look for any contact information in the marketing contacts tab
                                contact_elements = driver.find_elements(By.CSS_SELECTOR, '.tab-content p, .tab-content div')
                                contact_info = []
                                
                                for elem in contact_elements:
                                    try:
                                        text = elem.text.strip()
                                        if text and text not in ['Marketing Contacts', '']:
                                            contact_info.append(text)
                                    except:
                                        continue
                                
                                if contact_info:
                                    household_data['Contacts'] = contact_info
                                    
                            except Exception as e:
                                logger.error(f"  ⚠️ Error extracting marketing contacts: {e}")
                        
                        # Store the extracted data
                        if household_data:
                            content = json.dumps(household_data)
                            property_data[column_name] = content
                            logger.info(f"  ✅ {tab_name} extracted: {len(household_data)} fields")
                            
                            # Also store individual fields for database compatibility
                            if tab_name == 'Owner Information':
                                property_data['Owner_Name'] = household_data.get('Name', '')
                                property_data['Current_Tenure'] = household_data.get('Current Tenure', '')
                                property_data['Owner_Type'] = household_data.get('Owner Type', '')
                            elif tab_name == 'Marketing Contacts':
                                property_data['Marketing_Contacts_JSON'] = content
                        else:
                            property_data[column_name] = 'No data available'
                            logger.warning(f"  ⚠️ {tab_name} - no data found")
                            
                    else:
                        property_data[column_name] = 'Tab not available'
                        logger.warning(f"  ⚠️ {tab_name} tab not available")
                except Exception as e:
                    property_data[column_name] = 'Not available'
                    logger.error(f"  ❌ {tab_name} extraction failed: {e}")
        except Exception as e:
            logger.error(f"  ❌ Household information extraction failed: {e}")
            property_data['Household_Information_Owner_Information'] = 'Not available'
            property_data['Household_Information_Marketing_Contacts'] = 'Not available'
            property_data['Owner_Name'] = ''
            property_data['Current_Tenure'] = ''
            property_data['Owner_Type'] = ''
            property_data['Marketing_Contacts_JSON'] = json.dumps([])
        
        # Extract Valuation Estimates
        try:
            valuation_tabs = {
                'Valuation Estimate': 'Valuation_Estimate_Estimate',
                'Rental Estimate': 'Valuation_Estimate_Rental'
            }
            
            for tab_name, column_name in valuation_tabs.items():
                try:
                    tab_element = driver.find_element(By.CSS_SELECTOR, f'[data-testid="crux-tab-menu-{tab_name}"]')
                    if tab_element and tab_element.is_enabled():
                        driver.execute_script("arguments[0].click();", tab_element)
                        time.sleep(2)
                        
                        error_content = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-detail"] .error-fetching span')
                        if error_content:
                            property_data[column_name] = error_content
                        else:
                            valuation_data = {}
                            
                            confidence = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-detail"] .confidence')
                            if confidence:
                                valuation_data['confidence'] = confidence
                            
                            if tab_name == 'Valuation Estimate':
                                low_value = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-range"] .valuation-range-footer .flex-grow:first-child .author')
                                estimate_value = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-range"] .valuation-range-footer .flex-grow:nth-child(2) .legend .author')
                                high_value = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-range"] .valuation-range-footer .flex-grow:last-child .author')
                                
                                if low_value or estimate_value or high_value:
                                    valuation_data['low_value'] = low_value
                                    valuation_data['estimate_value'] = estimate_value
                                    valuation_data['high_value'] = high_value
                                    
                                    summary_parts = []
                                    if low_value:
                                        summary_parts.append(f"Low: {low_value}")
                                    if estimate_value:
                                        summary_parts.append(f"Estimate: {estimate_value}")
                                    if high_value:
                                        summary_parts.append(f"High: {high_value}")
                                    if confidence:
                                        summary_parts.append(f"Confidence: {confidence}")
                                    
                                    property_data[column_name] = " | ".join(summary_parts)
                                    
                                    if valuation_data:
                                        property_data[f'{column_name}_JSON'] = json.dumps(valuation_data)
                                else:
                                    content = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-detail"]')
                                    property_data[column_name] = content if content else 'Not available'
                            
                            elif tab_name == 'Rental Estimate':
                                rental_data = {}
                                
                                if confidence:
                                    rental_data['confidence'] = confidence
                                
                                try:
                                    yield_elem = driver.find_element(By.CSS_SELECTOR, '#rental-avm-details')
                                    if yield_elem:
                                        yield_text = yield_elem.text.strip()
                                        yield_match = re.search(r'(\d+\.?\d*%)', yield_text)
                                        if yield_match:
                                            rental_data['rental_yield'] = yield_match.group(1)
                                except:
                                    pass
                                
                                low_value = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-range"] .valuation-range-footer .flex-grow:first-child .author')
                                estimate_value = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-range"] .valuation-range-footer .flex-grow:nth-child(2) .legend .author')
                                high_value = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-range"] .valuation-range-footer .flex-grow:last-child .author')
                                
                                if low_value or estimate_value or high_value:
                                    rental_data['low_value'] = low_value
                                    rental_data['estimate_value'] = estimate_value
                                    rental_data['high_value'] = high_value
                                    
                                    summary_parts = []
                                    if low_value:
                                        summary_parts.append(f"Low: {low_value}")
                                    if estimate_value:
                                        summary_parts.append(f"Estimate: {estimate_value}")
                                    if high_value:
                                        summary_parts.append(f"High: {high_value}")
                                    if rental_data.get('rental_yield'):
                                        summary_parts.append(f"Yield: {rental_data['rental_yield']}")
                                    if confidence:
                                        summary_parts.append(f"Confidence: {confidence}")
                                    
                                    property_data[column_name] = " | ".join(summary_parts)
                                    
                                    if rental_data:
                                        property_data[f'{column_name}_JSON'] = json.dumps(rental_data)
                                else:
                                    content = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-detail"]')
                                    property_data[column_name] = content if content else 'Not available'
                    else:
                        property_data[column_name] = 'Tab not available'
                except Exception as e:
                    property_data[column_name] = 'Not available'
        except Exception as e:
            logger.error(f"  ❌ Valuation estimate extraction failed: {e}")
        
        # Extract Nearby Schools
        try:
            schools_tabs = {
                'In Catchment': 'Nearby_Schools_In_Catchment',
                'All Nearby': 'Nearby_Schools_All_Nearby'
            }
            
            for tab_name, column_name in schools_tabs.items():
                try:
                    tab_element = driver.find_element(By.CSS_SELECTOR, f'[data-testid="crux-tab-menu-{tab_name}"]')
                    if tab_element and tab_element.is_enabled():
                        driver.execute_script("arguments[0].click();", tab_element)
                        time.sleep(3)
                        
                        error_content = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="nearby-school-panel"] .error-fetching span')
                        if error_content:
                            property_data[column_name] = error_content
                        else:
                            schools_data = []
                            
                            # Handle scrollable content
                            try:
                                scroll_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="nearby-school-panel"] .simplebar-content')
                                
                                last_height = 0
                                scroll_attempts = 0
                                max_scroll_attempts = 5
                                
                                while scroll_attempts < max_scroll_attempts:
                                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
                                    time.sleep(1)
                                    
                                    current_height = driver.execute_script("return arguments[0].scrollHeight", scroll_container)
                                    if current_height == last_height:
                                        break
                                    
                                    last_height = current_height
                                    scroll_attempts += 1
                            except:
                                pass
                            
                            # Get all school list items
                            school_items = driver.find_elements(By.CSS_SELECTOR, '[data-testid="nearby-school-panel"] ul.nearby-school-list-container li[data-testid="list-template"]')
                            
                            for school_item in school_items:
                                try:
                                    school_info = {}
                                    
                                    name_elem = school_item.find_element(By.CSS_SELECTOR, '.school-name')
                                    school_info['name'] = name_elem.text.strip()
                                    
                                    address_elem = school_item.find_element(By.CSS_SELECTOR, '.place-address')
                                    school_info['address'] = address_elem.text.strip()
                                    
                                    distance_elem = school_item.find_element(By.CSS_SELECTOR, '.school-distance')
                                    school_info['distance'] = distance_elem.text.strip()
                                    
                                    attributes = {}
                                    
                                    try:
                                        type_elem = school_item.find_element(By.CSS_SELECTOR, '[data-testid="schoolType"] .MuiChip-label')
                                        attributes['type'] = type_elem.text.strip()
                                    except:
                                        attributes['type'] = ''
                                    
                                    try:
                                        sector_elem = school_item.find_element(By.CSS_SELECTOR, '[data-testid="schoolSector"] .MuiChip-label')
                                        attributes['sector'] = sector_elem.text.strip()
                                    except:
                                        attributes['sector'] = ''
                                    
                                    try:
                                        gender_elem = school_item.find_element(By.CSS_SELECTOR, '[data-testid="schoolGender"] .MuiChip-label')
                                        attributes['gender'] = gender_elem.text.strip()
                                    except:
                                        attributes['gender'] = ''
                                    
                                    try:
                                        year_elem = school_item.find_element(By.CSS_SELECTOR, '[data-testid="schoolYearLevels"] .MuiChip-label')
                                        attributes['year_levels'] = year_elem.text.strip()
                                    except:
                                        attributes['year_levels'] = ''
                                    
                                    try:
                                        enroll_elem = school_item.find_element(By.CSS_SELECTOR, '[data-testid="schoolEnrollments"] .MuiChip-label')
                                        attributes['enrollments'] = enroll_elem.text.strip()
                                    except:
                                        attributes['enrollments'] = ''
                                    
                                    school_info['attributes'] = attributes
                                    schools_data.append(school_info)
                                    
                                except Exception as school_error:
                                    continue
                            
                            property_data[column_name] = json.dumps(schools_data) if schools_data else "[]"
                    else:
                        property_data[column_name] = 'Tab not available'
                except Exception as e:
                    property_data[column_name] = 'Not available'
        except Exception as e:
            logger.error(f"  ❌ Nearby schools extraction failed: {e}")
        
        # Extract Property History using the same method as sales_scraping.py
        try:
            history_tabs = {
                'All': 'Property_History_All',
                'Sale': 'Property_History_Sale',
                'Listing': 'Property_History_Listing',
                'Rental': 'Property_History_Rental',
                'DA': 'Property_History_DA'
            }
            
            for tab_name, column_name in history_tabs.items():
                try:
                    # Use the same XPath selectors as sales_scraping.py
                    tab_element = None
                    tab_selectors = [
                        f"//div[@role='presentation' and contains(@class, 'property-timeline__timeline--tab') and contains(text(), '{tab_name}')]",
                        f"//div[contains(@class, 'property-timeline__timeline--tab') and contains(text(), '{tab_name}')]",
                        f"//div[@role='presentation' and text()='{tab_name}']",
                        f"//div[contains(@class, 'timeline--tab') and contains(text(), '{tab_name}')]"
                    ]
                    
                    for selector in tab_selectors:
                        try:
                            tab_element = driver.find_element(By.XPATH, selector)
                            if tab_element and tab_element.is_displayed():
                                logger.info(f"✅ Found {tab_name} tab with selector: {selector}")
                                break
                        except:
                            continue
                    
                    if not tab_element:
                        logger.warning(f"❌ Could not find {tab_name} tab with any selector")
                        property_data[column_name] = 'Tab not found'
                        continue
                    
                    if tab_element.is_enabled():
                        driver.execute_script("arguments[0].click();", tab_element)
                        time.sleep(2)  # Wait for content to load
                        
                        # Use frontend-friendly structure
                        history_data = {
                            "events": [],
                            "total_events": 0,
                            "last_sale": None,
                            "last_rental": None,
                            "last_listing": None,
                            "events_by_type": {
                                "sale": [],
                                "rental": [],
                                "listing": [],
                                "other": []
                            }
                        }
                        
                        # Try to find timeline items using the same selectors as sales_scraping.py
                        timeline_items = []
                        timeline_selectors = [
                            '.property-timeline__timeline--tab-content ul li',
                            '.property-timeline__timeline--tab-content li',
                            '.timeline--tab-content ul li',
                            '.timeline--tab-content li',
                            '[data-testid="timeline-item"]',
                            '.timeline-item'
                        ]
                        
                        for selector in timeline_selectors:
                            try:
                                timeline_items = driver.find_elements(By.CSS_SELECTOR, selector)
                                if timeline_items:
                                    break
                            except:
                                continue
                        
                        for item in timeline_items:
                            try:
                                event = {}
                                
                                # Extract date using the same selectors as sales_scraping.py
                                date_selectors = ['.date-circle .circle', '.date-circle', '.timeline-date', '.date', '[data-testid="timeline-date"]']
                                for date_selector in date_selectors:
                                    try:
                                        date_elem = item.find_element(By.CSS_SELECTOR, date_selector)
                                        event["date"] = date_elem.text.strip()
                                        break
                                    except:
                                        continue
                                
                                # Extract event type/description using the same selectors as sales_scraping.py
                                desc_selectors = ['.prop-info .heading', '.prop-info .title', '.timeline-title', '.heading', '.title', '[data-testid="timeline-title"]']
                                for desc_selector in desc_selectors:
                                    try:
                                        desc_elem = item.find_element(By.CSS_SELECTOR, desc_selector)
                                        event["description"] = desc_elem.text.strip()
                                        break
                                    except:
                                        continue
                                
                                # Extract details using the same selectors as sales_scraping.py
                                details = []
                                detail_selectors = ['.prop-info .details', '.timeline-details', '.details', '.info']
                                for detail_selector in detail_selectors:
                                    try:
                                        detail_elems = item.find_elements(By.CSS_SELECTOR, detail_selector)
                                        for detail in detail_elems:
                                            detail_text = detail.text.strip()
                                            if detail_text:
                                                details.append(detail_text)
                                        if details:
                                            break
                                    except:
                                        continue
                                
                                if details:
                                    event["details"] = details
                                
                                # Determine event type and organize data
                                if event.get("description", "").lower() in ["sold", "sale"]:
                                    event["type"] = "sale"
                                    if not history_data["last_sale"]:
                                        history_data["last_sale"] = event
                                    history_data["events_by_type"]["sale"].append(event)
                                elif event.get("description", "").lower() in ["rented", "rental", "lease"]:
                                    event["type"] = "rental"
                                    if not history_data["last_rental"]:
                                        history_data["last_rental"] = event
                                    history_data["events_by_type"]["rental"].append(event)
                                elif event.get("description", "").lower() in ["listed", "listing"]:
                                    event["type"] = "listing"
                                    if not history_data["last_listing"]:
                                        history_data["last_listing"] = event
                                    history_data["events_by_type"]["listing"].append(event)
                                else:
                                    event["type"] = "other"
                                    history_data["events_by_type"]["other"].append(event)
                                
                                if event.get("date") or event.get("description"):
                                    history_data["events"].append(event)
                                    
                            except Exception as e:
                                logger.error(f"⚠️ Error extracting timeline item: {e}")
                                continue
                        
                        history_data["total_events"] = len(history_data["events"])
                        
                        # Use both JSON and fallback text extraction like sales_scraping.py
                        history_json = json.dumps(history_data) if history_data["events"] else "{}"
                        
                        # Also extract as simple text items for fallback
                        history_items = []
                        for item in timeline_items:
                            try:
                                # Extract date
                                date_text = ""
                                date_selectors = ['.date-circle .circle', '.date-circle', '.timeline-date', '.date', '[data-testid="timeline-date"]']
                                for date_selector in date_selectors:
                                    try:
                                        date_elem = item.find_element(By.CSS_SELECTOR, date_selector)
                                        date_text = date_elem.text.strip()
                                        if date_text:
                                            break
                                    except:
                                        continue
                                
                                # Extract description
                                desc_text = ""
                                desc_selectors = ['.prop-info .heading', '.prop-info .title', '.timeline-title', '.heading', '.title', '[data-testid="timeline-title"]']
                                for desc_selector in desc_selectors:
                                    try:
                                        desc_elem = item.find_element(By.CSS_SELECTOR, desc_selector)
                                        desc_text = desc_elem.text.strip()
                                        if desc_text:
                                            break
                                    except:
                                        continue
                                
                                # Extract details
                                details = []
                                detail_selectors = ['.prop-info .details', '.timeline-details', '.details', '.info']
                                for detail_selector in detail_selectors:
                                    try:
                                        detail_elems = item.find_elements(By.CSS_SELECTOR, detail_selector)
                                        for detail in detail_elems:
                                            detail_text = detail.text.strip()
                                            if detail_text:
                                                details.append(detail_text)
                                        if details:
                                            break
                                    except:
                                        continue
                                
                                # Create history item
                                if date_text or desc_text:
                                    history_item = f"{date_text}: {desc_text}" if date_text and desc_text else (date_text or desc_text)
                                    if details:
                                        history_item += f" ({'; '.join(details)})"
                                    history_items.append(history_item)
                                else:
                                    # Fallback: get all text from the item
                                    item_text = item.text.strip()
                                    if item_text:
                                        history_items.append(item_text)
                            except Exception as e:
                                continue
                        
                        # Use JSON if available, otherwise use text items
                        property_data[column_name] = history_json if history_json != "{}" else ' | '.join(history_items)
                        logger.info(f"✅ {tab_name} history extracted: {len(history_data['events'])} JSON events, {len(history_items)} text items")
                    else:
                        property_data[column_name] = 'Tab not available'
                except Exception as e:
                    property_data[column_name] = 'Not available'
                    logger.error(f"❌ {tab_name} history extraction failed: {e}")
        except Exception as e:
            logger.error(f"  ❌ Property history extraction failed: {e}")
        
        logger.info(f"✅ Successfully extracted comprehensive property data")
        return property_data
        
    except Exception as e:
        logger.error(f"❌ Error extracting property data: {e}")
        return None
