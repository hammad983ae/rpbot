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

def extract_key_value_pairs(driver, container_selector, key_selector=".key", value_selector=".value"):
    """Extract key-value pairs from a container and return as JSON object."""
    try:
        container = driver.find_element(By.CSS_SELECTOR, container_selector)
        key_elements = container.find_elements(By.CSS_SELECTOR, key_selector)
        value_elements = container.find_elements(By.CSS_SELECTOR, value_selector)
        
        data = {}
        for i, key_elem in enumerate(key_elements):
            if i < len(value_elements):
                key = key_elem.text.strip()
                value = value_elements[i].text.strip()
                if key and value:
                    data[key] = value
        
        return json.dumps(data) if data else "{}"
    except Exception as e:
        print(f"  ⚠️ Key-value extraction failed: {e}")
        return "{}"

def extract_legal_description_json(driver):
    """Extract legal description data as structured JSON."""
    try:
        # Look for key-value pairs in the legal description section
        legal_data = {}
        
        # Try to find structured data elements
        try:
            # Look for specific legal description fields
            rpd = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="legal-rpd"] .attr-value')
            zoning = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="legal-zoning"] .attr-value')
            title_ref = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="legal-title-ref"] .attr-value')
            title_indicator = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="legal-title-indicator"] .attr-value')
            la = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="legal-la"] .attr-value')
            issue_date = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="legal-issue-date"] .attr-value')
            fee_code = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="legal-fee-code"] .attr-value')
            
            if rpd: legal_data["RPD"] = rpd
            if zoning: legal_data["Zoning"] = zoning
            if title_ref: legal_data["Title Ref"] = title_ref
            if title_indicator: legal_data["Title Indicator"] = title_indicator
            if la: legal_data["LA"] = la
            if issue_date: legal_data["Issue Date"] = issue_date
            if fee_code: legal_data["Fee Code"] = fee_code
            
        except Exception as e:
            print(f"  ⚠️ Structured legal data extraction failed: {e}")
        
        # Fallback: try to extract from any key-value pairs in the legal description area
        if not legal_data:
            try:
                legal_container = driver.find_element(By.CSS_SELECTOR, '#legal-description, .legal-description, [data-testid="legal-description"]')
                # Look for any structured data within
                rows = legal_container.find_elements(By.CSS_SELECTOR, 'tr, .row, .field')
                for row in rows:
                    try:
                        key_elem = row.find_element(By.CSS_SELECTOR, 'td:first-child, .key, .label, strong')
                        value_elem = row.find_element(By.CSS_SELECTOR, 'td:last-child, .value, .data')
                        key = key_elem.text.strip().rstrip(':')
                        value = value_elem.text.strip()
                        if key and value:
                            legal_data[key] = value
                    except:
                        continue
            except Exception as e:
                print(f"  ⚠️ Fallback legal data extraction failed: {e}")
        
        return json.dumps(legal_data) if legal_data else "{}"
    except Exception as e:
        print(f"  ❌ Legal description JSON extraction failed: {e}")
        return "{}"

def extract_property_features_json(driver):
    """Extract property features as structured JSON."""
    try:
        features_data = {}
        
        # Try to extract structured property features
        try:
            # Look for property feature elements
            feature_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="property-feature"], .property-feature, .feature-item')
            for feature in feature_elements:
                try:
                    key_elem = feature.find_element(By.CSS_SELECTOR, '.feature-name, .feature-key, strong, .label')
                    value_elem = feature.find_element(By.CSS_SELECTOR, '.feature-value, .feature-data, .value')
                    key = key_elem.text.strip().rstrip(':')
                    value = value_elem.text.strip()
                    if key and value:
                        features_data[key] = value
                except:
                    continue
        except Exception as e:
            print(f"  ⚠️ Structured features extraction failed: {e}")
        
        return json.dumps(features_data) if features_data else "{}"
    except Exception as e:
        print(f"  ❌ Property features JSON extraction failed: {e}")
        return "{}"

def extract_land_values_json(driver):
    """Extract land values as structured JSON."""
    try:
        land_values_data = {}
        
        # Try to extract structured land value data
        try:
            # Look for land value elements
            value_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="land-value"], .land-value, .value-item')
            for value_item in value_elements:
                try:
                    key_elem = value_item.find_element(By.CSS_SELECTOR, '.value-name, .value-key, strong, .label')
                    value_elem = value_item.find_element(By.CSS_SELECTOR, '.value-amount, .value-data, .value')
                    key = key_elem.text.strip().rstrip(':')
                    value = value_elem.text.strip()
                    if key and value:
                        land_values_data[key] = value
                except:
                    continue
        except Exception as e:
            print(f"  ⚠️ Structured land values extraction failed: {e}")
        
        return json.dumps(land_values_data) if land_values_data else "{}"
    except Exception as e:
        print(f"  ❌ Land values JSON extraction failed: {e}")
        return "{}"

def extract_property_history_json(driver, tab_name):
    """Extract property history as structured JSON."""
    try:
        history_data = {
            "events": [],
            "summary": {
                "total_events": 0,
                "last_sale": None,
                "last_rental": None,
                "last_listing": None
            }
        }
        
        # Try to find timeline items
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
                
                # Extract date
                date_selectors = ['.date-circle .circle', '.date-circle', '.timeline-date', '.date', '[data-testid="timeline-date"]']
                for date_selector in date_selectors:
                    try:
                        date_elem = item.find_element(By.CSS_SELECTOR, date_selector)
                        event["date"] = date_elem.text.strip()
                        break
                    except:
                        continue
                
                # Extract event type/description
                desc_selectors = ['.prop-info .heading', '.prop-info .title', '.timeline-title', '.heading', '.title', '[data-testid="timeline-title"]']
                for desc_selector in desc_selectors:
                    try:
                        desc_elem = item.find_element(By.CSS_SELECTOR, desc_selector)
                        event["description"] = desc_elem.text.strip()
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
                
                if details:
                    event["details"] = details
                
                # Determine event type
                if event.get("description", "").lower() in ["sold", "sale"]:
                    event["type"] = "sale"
                    if not history_data["summary"]["last_sale"]:
                        history_data["summary"]["last_sale"] = event
                elif event.get("description", "").lower() in ["rented", "rental", "lease"]:
                    event["type"] = "rental"
                    if not history_data["summary"]["last_rental"]:
                        history_data["summary"]["last_rental"] = event
                elif event.get("description", "").lower() in ["listed", "listing"]:
                    event["type"] = "listing"
                    if not history_data["summary"]["last_listing"]:
                        history_data["summary"]["last_listing"] = event
                else:
                    event["type"] = "other"
                
                if event.get("date") or event.get("description"):
                    history_data["events"].append(event)
                    
            except Exception as e:
                print(f"⚠️ Error extracting timeline item: {e}")
                continue
        
        history_data["summary"]["total_events"] = len(history_data["events"])
        
        return json.dumps(history_data) if history_data["events"] else "{}"
    except Exception as e:
        print(f"  ❌ Property history JSON extraction failed: {e}")
        return "{}"

def extract_property_data(driver, url):
    """Extract comprehensive property data from a single property page."""
    print(f"🔍 Scraping property: {url}")
    
    try:
        print(f"🌐 Loading URL: {url}")
        driver.get(url)
        
        # Wait for initial page load
        time.sleep(5)
        
        # Check if page loaded successfully
        current_url = driver.current_url
        print(f"Current URL after load: {current_url}")
        
        # Check for common error pages or redirects
        if "error" in current_url.lower() or "404" in current_url.lower():
            print("❌ Error page detected")
            return None
        
        # Wait for the main content to load with multiple attempts
        max_attempts = 5
        page_loaded = False
        
        for attempt in range(max_attempts):
            try:
                print(f"⏳ Waiting for page content (attempt {attempt + 1}/{max_attempts})")
                
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
                        print(f"✅ Found content with selector: {selector}")
                        page_loaded = True
                        break
                    except:
                        continue
                
                if page_loaded:
                    break
                    
            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    print(f"Retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    print("⚠️ Main content not loaded after all attempts, continuing anyway...")
        
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
            # JSON structured data columns
            'Property_Attributes_JSON': '',
            'Sale_Information_JSON': '',
            'Natural_Risks_JSON': '',
            'Scraping_Date': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Debug: Check what elements are available
        print("🔍 Debugging page elements...")
        try:
            # Check if address element exists
            address_elements = driver.find_elements(By.ID, "attr-single-line-address")
            print(f"  Address elements found: {len(address_elements)}")
            
            # Check for any h4 elements
            h4_elements = driver.find_elements(By.TAG_NAME, "h4")
            print(f"  H4 elements found: {len(h4_elements)}")
            
            # Check for property attributes
            bed_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="property-attr-bed"]')
            print(f"  Bedroom elements found: {len(bed_elements)}")
            
            
        except Exception as e:
            print(f"  Debug error: {e}")
        
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
                print(f"  ✅ Address extracted from URL: {address_text}")
            else:
                property_data['Address'] = ''
                print(f"  ❌ Could not parse address from URL: {url}")
        except Exception as e:
            property_data['Address'] = ''
            print(f"  ❌ Address extraction from URL failed: {e}")
        
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
            print(f"  ✅ Bedrooms extracted: {property_data['Bedrooms']}")
        except Exception as e:
            property_data['Bedrooms'] = '-'
            property_attributes['bedrooms'] = '-'
            print(f"  ❌ Bedrooms extraction failed: {e}")
            
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
                    print("  🔍 Found 'Show More' link, clicking to expand description...")
                    driver.execute_script("arguments[0].click();", show_more_link)
                    time.sleep(2)  # Wait for content to expand
            except NoSuchElementException:
                # No "Show More" link found, continue with current content
                pass
            
            # Get the full description text
            property_data['Listing_Description'] = desc_elem.text.strip()
            print(f"  ✅ Listing description extracted: {len(property_data['Listing_Description'])} characters")
        except Exception as e:
            print(f"  ❌ Listing description extraction failed: {e}")
            property_data['Listing_Description'] = ''
        
        # Extract owner type
        try:
            owner_type = safe_get_text(driver, By.CSS_SELECTOR, '.owner-type')
            property_data['Owner_Type'] = owner_type
        except:
            pass
        
        # Extract current tenure
        try:
            tenure = safe_get_text(driver, By.CSS_SELECTOR, '.tenure')
            property_data['Current_Tenure'] = tenure
        except:
            pass
        
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
                        print(f"  ✅ Found structured agent info in description")
                    else:
                        # Fallback to pattern matching if structured labels not found
                        print(f"  🔍 Using pattern matching fallback for agent info")
                        
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
                    print(f"  ⚠️ Text-based agent extraction failed: {text_extract_error}")
            
            # Store agent information as JSON if found
            if agent_info:
                property_data['Advertising_Agent_Info_JSON'] = json.dumps(agent_info)
                print(f"  ✅ Advertising agent info extracted: {len(agent_info)} fields")
            else:
                property_data['Advertising_Agent_Info_JSON'] = ''
                print(f"  ℹ️ No advertising agent information found")
        except Exception as e:
            print(f"  ⚠️ Advertising agent info extraction failed: {e}")
            property_data['Advertising_Agent_Info_JSON'] = ''
        
        # Extract Additional Information - separate tabs (Legal Description, Property Features, Land Values)
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
                                    print(f"  ⚠️ Error extracting legal row: {row_error}")
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
                                        print(f"  🔍 Found {len(rows)} feature rows with selector: {selector}")
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
                                    print(f"  ⚠️ Fallback extraction failed: {fallback_error}")
                            
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
                                    print(f"  ⚠️ Error extracting feature row: {row_error}")
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
                                        print(f"  🔍 Found {len(rows)} value rows with selector: {selector}")
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
                                    print(f"  ⚠️ Fallback extraction failed: {fallback_error}")
                            
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
                                    print(f"  ⚠️ Error extracting value row: {row_error}")
                                    continue
                            
                            content = json.dumps(values_data) if values_data else "{}"
                        
                        else:
                            # Fallback for other tabs
                            content = safe_get_text(driver, By.CSS_SELECTOR, '#additional-information-view .tab-content')
                            content = json.dumps({"raw_content": content}) if content else "{}"
                        
                        property_data[column_name] = content if content != "{}" else 'Not available'
                        print(f"  ✅ {tab_name} extracted: {len(content) if content else 0} characters")
                    else:
                        property_data[column_name] = 'Tab not available'
                        print(f"  ⚠️ {tab_name} tab not available")
                except Exception as e:
                    property_data[column_name] = 'Not available'
                    print(f"  ❌ {tab_name} extraction failed: {e}")
        except Exception as e:
            print(f"  ❌ Additional information extraction failed: {e}")
        
        # Extract Household Information - separate tabs (Owner Information, Marketing Contacts)
        try:
            household_tabs = {
                'Owner Information': 'Household_Information_Owner_Information',
                'Marketing Contacts': 'Household_Information_Marketing_Contacts'
            }
            
            for tab_name, column_name in household_tabs.items():
                try:
                    # Try to click on the specific tab
                    tab_element = driver.find_element(By.CSS_SELECTOR, f'[data-testid="crux-tab-menu-{tab_name}"]')
                    if tab_element and tab_element.is_enabled():
                        driver.execute_script("arguments[0].click();", tab_element)
                        time.sleep(2)  # Wait for content to load
                        
                        # Extract content
                        content = safe_get_text(driver, By.CSS_SELECTOR, '.ownership-detail')
                        property_data[column_name] = content if content else 'Not available'
                        print(f"  ✅ {tab_name} extracted: {len(content) if content else 0} characters")
                    else:
                        property_data[column_name] = 'Tab not available'
                        print(f"  ⚠️ {tab_name} tab not available")
                except Exception as e:
                    property_data[column_name] = 'Not available'
                    print(f"  ❌ {tab_name} extraction failed: {e}")
        except Exception as e:
            print(f"  ❌ Household information extraction failed: {e}")
        
        # Extract market trends - properties sold in last 12 months
        try:
            properties_sold = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="metric-id-37"] .value')
            property_data['Properties_Sold_12_Months'] = properties_sold
        except:
            pass
        
        # Extract Property History - separate tabs (All, Sale, Listing, Rental, DA)
        try:
            history_tabs = {
                'All': 'Property_History_All',
                'Sale': 'Property_History_Sale', 
                'Listing': 'Property_History_Listing',
                'Rental': 'Property_History_Rental',
                'DA': 'Property_History_DA'
            }
            
            # Debug: Print available timeline tabs
            try:
                all_tabs = driver.find_elements(By.CSS_SELECTOR, '.property-timeline__timeline--tab')
                print(f"🔍 Found {len(all_tabs)} timeline tabs:")
                for tab in all_tabs:
                    print(f"  - '{tab.text}' (class: {tab.get_attribute('class')})")
            except Exception as e:
                print(f"⚠️ Could not debug timeline tabs: {e}")
            
            for tab_name, column_name in history_tabs.items():
                try:
                    # Try to click on the specific tab using multiple selector strategies
                    # Based on the HTML: <div role="presentation" class="property-timeline__timeline--tab">All</div>
                    tab_element = None
                    
                    # Try multiple selectors for the tab
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
                                print(f"✅ Found {tab_name} tab with selector: {selector}")
                                break
                        except NoSuchElementException:
                            continue
                    
                    if not tab_element:
                        print(f"❌ Could not find {tab_name} tab with any selector")
                        continue
                    
                    # Click the tab if it's enabled
                    if tab_element.is_enabled():
                        driver.execute_script("arguments[0].click();", tab_element)
                        time.sleep(2)  # Wait for content to load
                        
                        # Extract history items from this tab
                        history_items = []
                        
                        # Try multiple selectors for timeline content
                        timeline_selectors = [
                            '.property-timeline__timeline--tab-content ul li',
                            '.property-timeline__timeline--tab-content li',
                            '.timeline--tab-content ul li',
                            '.timeline--tab-content li',
                            '[data-testid="timeline-item"]',
                            '.timeline-item'
                        ]
                        
                        timeline_items = []
                        for selector in timeline_selectors:
                            try:
                                timeline_items = driver.find_elements(By.CSS_SELECTOR, selector)
                                if timeline_items:
                                    print(f"✅ Found {len(timeline_items)} timeline items with selector: {selector}")
                                    break
                            except Exception as e:
                                continue
                        
                        if not timeline_items:
                            print(f"⚠️ No timeline items found for {tab_name} tab")
                            # Check if there's a "no history" message
                            try:
                                no_history = driver.find_element(By.CSS_SELECTOR, '.no-history')
                                if no_history and no_history.is_displayed():
                                    print(f"ℹ️ {tab_name} tab shows: {no_history.text}")
                            except NoSuchElementException:
                                pass
                        
                        for item in timeline_items:
                            try:
                                # Try multiple selectors for date
                                date_text = ""
                                date_selectors = [
                                    '.date-circle .circle',
                                    '.date-circle',
                                    '.timeline-date',
                                    '.date',
                                    '[data-testid="timeline-date"]'
                                ]
                                
                                for date_selector in date_selectors:
                                    try:
                                        date_elem = item.find_element(By.CSS_SELECTOR, date_selector)
                                        date_text = date_elem.text.strip()
                                        if date_text:
                                            break
                                    except NoSuchElementException:
                                        continue
                                
                                # Try multiple selectors for description
                                desc_text = ""
                                desc_selectors = [
                                    '.prop-info .heading',
                                    '.prop-info .title',
                                    '.timeline-title',
                                    '.heading',
                                    '.title',
                                    '[data-testid="timeline-title"]'
                                ]
                                
                                for desc_selector in desc_selectors:
                                    try:
                                        desc_elem = item.find_element(By.CSS_SELECTOR, desc_selector)
                                        desc_text = desc_elem.text.strip()
                                        if desc_text:
                                            break
                                    except NoSuchElementException:
                                        continue
                                
                                # Try multiple selectors for details
                                details = []
                                detail_selectors = [
                                    '.prop-info .details',
                                    '.timeline-details',
                                    '.details',
                                    '.info'
                                ]
                                
                                for detail_selector in detail_selectors:
                                    try:
                                        detail_elems = item.find_elements(By.CSS_SELECTOR, detail_selector)
                                        for detail in detail_elems:
                                            detail_text = detail.text.strip()
                                            if detail_text:
                                                details.append(detail_text)
                                        if details:
                                            break
                                    except NoSuchElementException:
                                        continue
                                
                                # Create history item if we have at least date or description
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
                                print(f"⚠️ Error extracting timeline item: {e}")
                                continue
                        
                        # Use JSON extraction for property history
                        history_json = extract_property_history_json(driver, tab_name)
                        property_data[column_name] = history_json if history_json != "{}" else ' | '.join(history_items)
                        print(f"  ✅ {tab_name} history extracted as JSON: {len(history_items)} items")
                    else:
                        property_data[column_name] = 'Tab not available'
                        print(f"  ⚠️ {tab_name} tab not available")
                except Exception as e:
                    property_data[column_name] = 'Not available'
                    print(f"  ❌ {tab_name} history extraction failed: {e}")
        except Exception as e:
            print(f"  ❌ Property history extraction failed: {e}")
        
        # Extract Natural Risks as JSON
        try:
            natural_risks_data = {
                "risks": [],
                "summary": "No information available"
            }
            
            # Try to get error message first
            error_message = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="natural-risks-panel"] .error-fetching span')
            if error_message:
                natural_risks_data["summary"] = error_message
                natural_risks_data["error"] = True
            else:
                # Try to get structured risk information using the correct selectors from the HTML
                # Based on the HTML structure: .MuiGrid-container .MuiGrid-direction-xs-column
                risk_containers = driver.find_elements(By.CSS_SELECTOR, '[data-testid="natural-risks-panel"] .MuiGrid-container .MuiGrid-direction-xs-column')
                
                print(f"  🔍 Found {len(risk_containers)} risk containers")
                
                for container in risk_containers:
                    try:
                        # Get the risk type (Flood Zone, Bushfire Zone) using .MuiTypography-body1
                        risk_type_elem = container.find_element(By.CSS_SELECTOR, '.MuiTypography-body1')
                        risk_type = risk_type_elem.text.strip()
                        
                        # Get the status (Not detected, Detected) using .MuiTypography-body2
                        status_elem = container.find_element(By.CSS_SELECTOR, '.MuiTypography-body2')
                        status = status_elem.text.strip()
                        
                        print(f"  🔍 Found risk: {risk_type} = {status}")
                        
                        # Filter out generic text and include all valid risk types
                        if risk_type and risk_type not in ["Natural Risks", "View on map", ""]:
                        natural_risks_data["risks"].append({
                                "type": risk_type,
                            "status": status,
                                "description": f"{risk_type}: {status}"
                            })
                    except Exception as container_error:
                        print(f"  ⚠️ Error extracting risk container: {container_error}")
                        continue
                
                # If no risks found with the main selector, try alternative selectors
                if not natural_risks_data["risks"]:
                    print(f"  🔍 Trying alternative selectors for natural risks...")
                    
                    # Try to find any risk-related text in the panel
                    try:
                        panel_text = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="natural-risks-panel"]')
                        print(f"  🔍 Panel text: {panel_text[:200]}...")
                        
                        # Look for patterns like "Flood Zone: Not detected"
                        import re
                        risk_patterns = [
                            r'(Flood Zone)[:\s]*([^,\n]+)',
                            r'(Bushfire Zone)[:\s]*([^,\n]+)',
                            r'(Fire Zone)[:\s]*([^,\n]+)',
                            r'(Storm Zone)[:\s]*([^,\n]+)'
                        ]
                        
                        for pattern in risk_patterns:
                            matches = re.findall(pattern, panel_text, re.IGNORECASE)
                            for match in matches:
                                risk_type = match[0].strip()
                                status = match[1].strip()
                                if risk_type and status:
                                    natural_risks_data["risks"].append({
                                        "type": risk_type,
                                        "status": status,
                                        "description": f"{risk_type}: {status}"
                                    })
                                    print(f"  🔍 Pattern match: {risk_type} = {status}")
                    except Exception as pattern_error:
                        print(f"  ⚠️ Pattern matching failed: {pattern_error}")
                
                if natural_risks_data["risks"]:
                    natural_risks_data["summary"] = f"Found {len(natural_risks_data['risks'])} risk(s): " + ", ".join([f"{r['type']} ({r['status']})" for r in natural_risks_data["risks"]])
                    natural_risks_data["error"] = False
                else:
                    natural_risks_data["summary"] = "No risks identified"
                    natural_risks_data["error"] = False
            
            # Store both JSON and plain text versions
            property_data['Natural_Risks'] = natural_risks_data["summary"]
            property_data['Natural_Risks_JSON'] = json.dumps(natural_risks_data)
            print(f"  ✅ Natural risks extracted: {natural_risks_data['summary']}")
        except Exception as e:
            print(f"  ❌ Natural risks extraction failed: {e}")
            property_data['Natural_Risks'] = 'Not available'
            property_data['Natural_Risks_JSON'] = '{}'
        
        # Extract Valuation Estimate - separate tabs (Valuation Estimate, Rental Estimate)
        try:
            valuation_tabs = {
                'Valuation Estimate': 'Valuation_Estimate_Estimate',
                'Rental Estimate': 'Valuation_Estimate_Rental'
            }
            
            for tab_name, column_name in valuation_tabs.items():
                try:
                    # Try to click on the specific tab
                    tab_element = driver.find_element(By.CSS_SELECTOR, f'[data-testid="crux-tab-menu-{tab_name}"]')
                    if tab_element and tab_element.is_enabled():
                        driver.execute_script("arguments[0].click();", tab_element)
                        time.sleep(2)  # Wait for content to load
                        
                        # Check for error message first
                        error_content = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-detail"] .error-fetching span')
                        if error_content:
                            property_data[column_name] = error_content
                        else:
                            # Extract structured valuation data
                            valuation_data = {}
                            
                            # Extract confidence level
                            confidence = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-detail"] .confidence')
                            if confidence:
                                valuation_data['confidence'] = confidence
                            
                            # Extract valuation range data
                            if tab_name == 'Valuation Estimate':
                                # Extract Low, Estimate, High values
                                low_value = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-range"] .valuation-range-footer .flex-grow:first-child .author')
                                estimate_value = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-range"] .valuation-range-footer .flex-grow:nth-child(2) .legend .author')
                                high_value = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-range"] .valuation-range-footer .flex-grow:last-child .author')
                                
                                if low_value or estimate_value or high_value:
                                    valuation_data['low_value'] = low_value
                                    valuation_data['estimate_value'] = estimate_value
                                    valuation_data['high_value'] = high_value
                                    
                                    # Create a readable summary
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
                                else:
                                    # Fallback to general content extraction
                                    content = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-detail"]')
                            property_data[column_name] = content if content else 'Not available'
                            
                            if tab_name == 'Rental Estimate':
                                # For Rental Estimate, extract structured rental data
                                rental_data = {}
                                
                                # Extract confidence level
                                confidence = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-detail"] .confidence')
                                if confidence:
                                    rental_data['confidence'] = confidence
                                
                                # Extract rental yield
                                yield_elem = driver.find_element(By.CSS_SELECTOR, '#rental-avm-details')
                                if yield_elem:
                                    yield_text = yield_elem.text.strip()
                                    # Extract percentage from text like "Estimated Rental Yield 1.8%"
                                    import re
                                    yield_match = re.search(r'(\d+\.?\d*%)', yield_text)
                                    if yield_match:
                                        rental_data['rental_yield'] = yield_match.group(1)
                                
                                # Extract rental range values
                                low_value = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-range"] .valuation-range-footer .flex-grow:first-child .author')
                                estimate_value = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-range"] .valuation-range-footer .flex-grow:nth-child(2) .legend .author')
                                high_value = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-range"] .valuation-range-footer .flex-grow:last-child .author')
                                
                                if low_value or estimate_value or high_value:
                                    rental_data['low_value'] = low_value
                                    rental_data['estimate_value'] = estimate_value
                                    rental_data['high_value'] = high_value
                                    
                                    # Create a readable summary
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
                                else:
                                    # Fallback to general content extraction
                                    content = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="avm-detail"]')
                                    property_data[column_name] = content if content else 'Not available'
                                
                                # Store structured data as JSON if we have rental data
                                if rental_data:
                                    property_data[f'{column_name}_JSON'] = json.dumps(rental_data)
                            
                            # Store structured data as JSON if we have valuation data
                            if valuation_data and tab_name == 'Valuation Estimate':
                                property_data[f'{column_name}_JSON'] = json.dumps(valuation_data)
                        
                        print(f"  ✅ {tab_name} extracted: {len(property_data[column_name]) if property_data[column_name] else 0} characters")
                    else:
                        property_data[column_name] = 'Tab not available'
                        print(f"  ⚠️ {tab_name} tab not available")
                except Exception as e:
                    property_data[column_name] = 'Not available'
                    print(f"  ❌ {tab_name} extraction failed: {e}")
        except Exception as e:
            print(f"  ❌ Valuation estimate extraction failed: {e}")
        
        # Extract Nearby Schools - separate tabs (In Catchment, All Nearby)
        try:
            schools_tabs = {
                'In Catchment': 'Nearby_Schools_In_Catchment',
                'All Nearby': 'Nearby_Schools_All_Nearby'
            }
            
            for tab_name, column_name in schools_tabs.items():
                try:
                    # Try to click on the specific tab
                    tab_element = driver.find_element(By.CSS_SELECTOR, f'[data-testid="crux-tab-menu-{tab_name}"]')
                    if tab_element and tab_element.is_enabled():
                        driver.execute_script("arguments[0].click();", tab_element)
                        time.sleep(3)  # Wait for content to load
                        
                        # Check for error message first
                        error_content = safe_get_text(driver, By.CSS_SELECTOR, '[data-testid="nearby-school-panel"] .error-fetching span')
                        if error_content:
                            property_data[column_name] = error_content
                        else:
                            # Extract structured school data
                            schools_data = []
                            
                            # Handle scrollable content - scroll through the school list to load all schools
                            try:
                                scroll_container = driver.find_element(By.CSS_SELECTOR, '[data-testid="nearby-school-panel"] .simplebar-content')
                                
                                # Scroll to load all schools
                                last_height = 0
                                scroll_attempts = 0
                                max_scroll_attempts = 5
                                
                                while scroll_attempts < max_scroll_attempts:
                                    # Scroll down
                                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
                                    time.sleep(1)
                                    
                                    # Check if we've reached the bottom
                                    current_height = driver.execute_script("return arguments[0].scrollHeight", scroll_container)
                                    if current_height == last_height:
                                        break
                                    
                                    last_height = current_height
                                    scroll_attempts += 1
                                
                                print(f"  📜 Scrolled through school list ({scroll_attempts} attempts)")
                            except Exception as scroll_error:
                                print(f"  ⚠️ Could not scroll school list: {scroll_error}")
                            
                            # Get all school list items after scrolling
                            school_items = driver.find_elements(By.CSS_SELECTOR, '[data-testid="nearby-school-panel"] ul.nearby-school-list-container li[data-testid="list-template"]')
                            
                            for school_item in school_items:
                                try:
                                    school_info = {}
                                    
                                    # Extract school name
                                    name_elem = school_item.find_element(By.CSS_SELECTOR, '.school-name')
                                    school_info['name'] = name_elem.text.strip()
                                    
                                    # Extract address
                                    address_elem = school_item.find_element(By.CSS_SELECTOR, '.place-address')
                                    school_info['address'] = address_elem.text.strip()
                                    
                                    # Extract distance
                                    distance_elem = school_item.find_element(By.CSS_SELECTOR, '.school-distance')
                                    school_info['distance'] = distance_elem.text.strip()
                                    
                                    # Extract school attributes (chips)
                                    attributes = {}
                                    
                                    # School Type
                                    try:
                                        type_elem = school_item.find_element(By.CSS_SELECTOR, '[data-testid="schoolType"] .MuiChip-label')
                                        attributes['type'] = type_elem.text.strip()
                                    except:
                                        attributes['type'] = ''
                                    
                                    # School Sector
                                    try:
                                        sector_elem = school_item.find_element(By.CSS_SELECTOR, '[data-testid="schoolSector"] .MuiChip-label')
                                        attributes['sector'] = sector_elem.text.strip()
                                    except:
                                        attributes['sector'] = ''
                                    
                                    # School Gender
                                    try:
                                        gender_elem = school_item.find_element(By.CSS_SELECTOR, '[data-testid="schoolGender"] .MuiChip-label')
                                        attributes['gender'] = gender_elem.text.strip()
                                    except:
                                        attributes['gender'] = ''
                                    
                                    # School Year Levels
                                    try:
                                        year_elem = school_item.find_element(By.CSS_SELECTOR, '[data-testid="schoolYear"] .MuiChip-label')
                                        attributes['year_levels'] = year_elem.text.strip()
                                    except:
                                        attributes['year_levels'] = ''
                                    
                                    # School Enrollments
                                    try:
                                        enroll_elem = school_item.find_element(By.CSS_SELECTOR, '[data-testid="schoolEnrolments"] .MuiChip-label')
                                        attributes['enrollments'] = enroll_elem.text.strip()
                                    except:
                                        attributes['enrollments'] = ''
                                    
                                    school_info['attributes'] = attributes
                                    schools_data.append(school_info)
                                    
                                except Exception as school_error:
                                    print(f"  ⚠️ Error extracting individual school: {school_error}")
                                    continue
                            
                            # Store as JSON
                            if schools_data:
                                property_data[column_name] = json.dumps(schools_data)
                                print(f"  ✅ {tab_name} extracted: {len(schools_data)} schools")
                            else:
                                property_data[column_name] = 'No schools found'
                                print(f"  ℹ️ {tab_name}: No schools found")
                        
                    else:
                        property_data[column_name] = 'Tab not available'
                        print(f"  ⚠️ {tab_name} tab not available")
                except Exception as e:
                    property_data[column_name] = 'Not available'
                    print(f"  ❌ {tab_name} extraction failed: {e}")
        except Exception as e:
            print(f"  ❌ Nearby schools extraction failed: {e}")
        
        
        # Debug: Print extracted data
        print(f"📊 Extracted data:")
        print(f"  Address: {property_data['Address']}")
        print(f"  Property Type: {property_data['Property_Type']}")
        print(f"  Land Size: {property_data['Land_Size']}")
        print(f"  Last Sold Price: {property_data['Last_Sold_Price']}")
        print(f"  Last Sold Date: {property_data['Last_Sold_Date']}")
        print(f"  Sold By: {property_data['Sold_By']}")
        print(f"  Advertisement Date: {property_data['Advertisement_Date']}")
        print(f"  Listing Description: {property_data['Listing_Description'][:100]}..." if property_data['Listing_Description'] else "  Listing Description: None")
        print(f"  Advertising Agent Info: {property_data['Advertising_Agent_Info_JSON'][:100]}..." if property_data['Advertising_Agent_Info_JSON'] else "  Advertising Agent Info: None")
        print(f"  Property History All: {property_data['Property_History_All'][:100]}..." if property_data['Property_History_All'] else "  Property History All: None")
        print(f"  Property History Sale: {property_data['Property_History_Sale'][:100]}..." if property_data['Property_History_Sale'] else "  Property History Sale: None")
        print(f"  Natural Risks: {property_data['Natural_Risks']}")
        print(f"  Valuation Estimate: {property_data['Valuation_Estimate_Estimate'][:100]}..." if property_data['Valuation_Estimate_Estimate'] else "  Valuation Estimate: None")
        print(f"  Valuation Estimate JSON: {property_data['Valuation_Estimate_Estimate_JSON'][:100]}..." if property_data['Valuation_Estimate_Estimate_JSON'] else "  Valuation Estimate JSON: None")
        print(f"  Rental Estimate: {property_data['Valuation_Estimate_Rental'][:100]}..." if property_data['Valuation_Estimate_Rental'] else "  Rental Estimate: None")
        print(f"  Rental Estimate JSON: {property_data['Valuation_Estimate_Rental_JSON'][:100]}..." if property_data['Valuation_Estimate_Rental_JSON'] else "  Rental Estimate JSON: None")
        print(f"  Schools In Catchment: {property_data['Nearby_Schools_In_Catchment'][:100]}..." if property_data['Nearby_Schools_In_Catchment'] else "  Schools In Catchment: None")
        print(f"  Schools All Nearby: {property_data['Nearby_Schools_All_Nearby'][:100]}..." if property_data['Nearby_Schools_All_Nearby'] else "  Schools All Nearby: None")
        print(f"  Legal Description: {property_data['Additional_Information_Legal_Description'][:100]}..." if property_data['Additional_Information_Legal_Description'] else "  Legal Description: None")
        print(f"  Property Features: {property_data['Additional_Information_Property_Features'][:100]}..." if property_data['Additional_Information_Property_Features'] else "  Property Features: None")
        print(f"  Land Values: {property_data['Additional_Information_Land_Values'][:100]}..." if property_data['Additional_Information_Land_Values'] else "  Land Values: None")
        print(f"  Owner Information: {property_data['Household_Information_Owner_Information'][:100]}..." if property_data['Household_Information_Owner_Information'] else "  Owner Information: None")
        print(f"  Marketing Contacts: {property_data['Household_Information_Marketing_Contacts'][:100]}..." if property_data['Household_Information_Marketing_Contacts'] else "  Marketing Contacts: None")
        
        # Print JSON structured data
        print(f"📋 JSON Structured Data:")
        print(f"  Property Attributes JSON: {property_data['Property_Attributes_JSON']}")
        print(f"  Sale Information JSON: {property_data['Sale_Information_JSON']}")
        print(f"  Advertising Agent Info JSON: {property_data['Advertising_Agent_Info_JSON']}")
        print(f"  Natural Risks JSON: {property_data['Natural_Risks_JSON']}")
        print(f"  Valuation Estimate JSON: {property_data['Valuation_Estimate_Estimate_JSON']}")
        print(f"  Rental Estimate JSON: {property_data['Valuation_Estimate_Rental_JSON']}")
        
        print(f"✅ Successfully scraped property data")
        return property_data
        
    except Exception as e:
        print(f"❌ Error scraping property {url}: {e}")
        return None

def scrape_all_properties():
    """Main function to scrape all properties from vic_links.csv"""
    
    # Read the CSV file with property URLs
    try:
        # df_links = pd.read_csv('vic_links.csv')
        # urls = df_links['Property_URL'].dropna().tolist()
        urls=['https://rpp.corelogic.com.au/property/47-wellington-parade-south-east-melbourne-vic-3002/17241185']
        print(f"📋 Found {len(urls)} property URLs to scrape")
    except Exception as e:
        print(f"❌ Error reading vic_links.csv: {e}")
        return
    
    # Setup Chrome driver
    options = Options()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(600)
    driver.set_script_timeout(600)
    
    try:
        # Login first
        print("🔐 Starting login process...")
        driver.get("https://rpp.corelogic.com.au/")
        print("✅ Login page loaded")
        
        # Wait for page to fully load
        time.sleep(3)
        
        # Check if we're already logged in
        try:
            current_url = driver.current_url
            print(f"Current URL after login page load: {current_url}")
            
            # If we're redirected to a different page, we might already be logged in
            if "login" not in current_url.lower() and "signin" not in current_url.lower():
                print("✅ Already logged in or redirected to main page")
            else:
                print("🔐 Proceeding with login...")
                
                username_field = wait_until_present(driver, By.ID, "username", timeout=10)
                username_field.clear()
                username_field.send_keys("delpg2021")
                print("✅ Username entered")
                
                password_field = wait_until_present(driver, By.ID, "password", timeout=10)
                password_field.clear()
                password_field.send_keys("FlatHead@2024")
                print("✅ Password entered")
                
                sign_on_button = wait_until_clickable(driver, By.ID, "signOnButton", timeout=10)
                sign_on_button.click()
                print("✅ Login button clicked")
                
                # Wait for login to complete and check for redirect
                time.sleep(20)
                current_url = driver.current_url
                print(f"URL after login attempt: {current_url}")
                
        except Exception as login_error:
            print(f"⚠️ Login error: {login_error}")
            print("Continuing anyway...")
        
        # Final wait to ensure we're ready
        time.sleep(3)
        
        # Scrape each property
        all_property_data = []
        for i, url in enumerate(urls, 1):
            print(f"\n📊 Processing property {i}/{len(urls)}")
            property_data = extract_property_data(driver, url)
            if property_data:
                all_property_data.append(property_data)
            
            # Add delay between requests to be respectful
            time.sleep(2)
        
        # Save to separate Excel files for each card type
        if all_property_data:
            print(f"\n💾 Saving data to separate Excel files...")
            
            # Create separate data structures for each card
            property_overview_data = []
            sale_rental_data = []
            household_data = []
            additional_info_data = []
            natural_risks_data = []
            schools_data = []
            valuation_data = []
            property_history_data = []
            
            for prop in all_property_data:
                # Property Overview Card
                property_overview_data.append({
                    'Property_URL': prop.get('Property_URL', ''),
                    'Address': prop.get('Address', ''),
                    'Property_Type': prop.get('Property_Type', ''),
                    'Land_Size': prop.get('Land_Size', ''),
                    'Floor_Area': prop.get('Floor_Area', ''),
                    'Bedrooms': prop.get('Bedrooms', ''),
                    'Bathrooms': prop.get('Bathrooms', ''),
                    'Car_Spaces': prop.get('Car_Spaces', ''),
                    'Scraping_Date': prop.get('Scraping_Date', '')
                })
                
                # Sale/Rental Information Card
                sale_rental_data.append({
                    'Property_URL': prop.get('Property_URL', ''),
                    'Address': prop.get('Address', ''),
                    'Last_Sold_Price': prop.get('Last_Sold_Price', ''),
                    'Last_Sold_Date': prop.get('Last_Sold_Date', ''),
                    'Sold_By': prop.get('Sold_By', ''),
                    'Land_Use': prop.get('Land_Use', ''),
                    'Issue_Date': prop.get('Issue_Date', ''),
                    'Advertisement_Date': prop.get('Advertisement_Date', ''),
                    'Listing_Description': prop.get('Listing_Description', ''),
                    'Advertising_Agent_Info_JSON': prop.get('Advertising_Agent_Info_JSON', ''),
                    'Sale_Information_JSON': prop.get('Sale_Information_JSON', ''),
                    'Scraping_Date': prop.get('Scraping_Date', '')
                })
                
                # Household Information Card
                household_data.append({
                    'Property_URL': prop.get('Property_URL', ''),
                    'Address': prop.get('Address', ''),
                    'Owner_Type': prop.get('Owner_Type', ''),
                    'Current_Tenure': prop.get('Current_Tenure', ''),
                    'Household_Information_Owner_Information': prop.get('Household_Information_Owner_Information', ''),
                    'Household_Information_Marketing_Contacts': prop.get('Household_Information_Marketing_Contacts', ''),
                    'Scraping_Date': prop.get('Scraping_Date', '')
                })
                
                # Additional Information Card
                additional_info_data.append({
                    'Property_URL': prop.get('Property_URL', ''),
                    'Address': prop.get('Address', ''),
                    'Additional_Information_Legal_Description': prop.get('Additional_Information_Legal_Description', ''),
                    'Additional_Information_Property_Features': prop.get('Additional_Information_Property_Features', ''),
                    'Additional_Information_Land_Values': prop.get('Additional_Information_Land_Values', ''),
                    'Scraping_Date': prop.get('Scraping_Date', '')
                })
                
                # Natural Risks Card
                natural_risks_data.append({
                    'Property_URL': prop.get('Property_URL', ''),
                    'Address': prop.get('Address', ''),
                    'Natural_Risks': prop.get('Natural_Risks', ''),
                    'Natural_Risks_JSON': prop.get('Natural_Risks_JSON', ''),
                    'Scraping_Date': prop.get('Scraping_Date', '')
                })
                
                # Schools Card
                schools_data.append({
                    'Property_URL': prop.get('Property_URL', ''),
                    'Address': prop.get('Address', ''),
                    'Nearby_Schools_In_Catchment': prop.get('Nearby_Schools_In_Catchment', ''),
                    'Nearby_Schools_All_Nearby': prop.get('Nearby_Schools_All_Nearby', ''),
                    'Scraping_Date': prop.get('Scraping_Date', '')
                })
                
                # Valuation Estimates Card
                valuation_data.append({
                    'Property_URL': prop.get('Property_URL', ''),
                    'Address': prop.get('Address', ''),
                    'Valuation_Estimate_Estimate': prop.get('Valuation_Estimate_Estimate', ''),
                    'Valuation_Estimate_Estimate_JSON': prop.get('Valuation_Estimate_Estimate_JSON', ''),
                    'Valuation_Estimate_Rental': prop.get('Valuation_Estimate_Rental', ''),
                    'Valuation_Estimate_Rental_JSON': prop.get('Valuation_Estimate_Rental_JSON', ''),
                    'Scraping_Date': prop.get('Scraping_Date', '')
                })
                
                # Property History Card
                property_history_data.append({
                    'Property_URL': prop.get('Property_URL', ''),
                    'Address': prop.get('Address', ''),
                    'Property_History_All': prop.get('Property_History_All', ''),
                    'Property_History_Sale': prop.get('Property_History_Sale', ''),
                    'Property_History_Listing': prop.get('Property_History_Listing', ''),
                    'Property_History_Rental': prop.get('Property_History_Rental', ''),
                    'Property_History_DA': prop.get('Property_History_DA', ''),
                    'Properties_Sold_12_Months': prop.get('Properties_Sold_12_Months', ''),
                    'Scraping_Date': prop.get('Scraping_Date', '')
                })
            
            # Save each card type to separate Excel files
            card_files = {
                'Property_Overview': property_overview_data,
                'Sale_Rental_Info': sale_rental_data,
                'Household_Info': household_data,
                'Additional_Info': additional_info_data,
                'Natural_Risks': natural_risks_data,
                'Schools': schools_data,
                'Valuation_Estimates': valuation_data,
                'Property_History': property_history_data
            }
            
            for card_name, card_data in card_files.items():
                if card_data:
                    df_card = pd.DataFrame(card_data)
                    filename = f'vic_property_{card_name.lower()}.xlsx'
                    df_card.to_excel(filename, index=False)
                    print(f"✅ Saved {len(card_data)} records to {filename}")
            
            # Also save a master file with all data for reference
            df_all = pd.DataFrame(all_property_data)
            df_all.to_excel('vic_property_master.xlsx', index=False)
            print(f"✅ Saved master file with all data to vic_property_master.xlsx")
            
            print(f"\n📊 Summary:")
            print(f"  - Total properties processed: {len(all_property_data)}")
            print(f"  - Card-specific files created: {len(card_files)}")
            print(f"  - Master file created: vic_property_master.xlsx")
        else:
            print("❌ No property data was successfully scraped")
            
    except Exception as e:
        print(f"❌ Error during scraping process: {e}")
    finally:
        driver.quit()
        print("🔚 Browser closed")

def test_save_separate_files(all_property_data):
    """Test function to save data to separate Excel files"""
    if not all_property_data:
        print("❌ No property data to save")
        return
    
    print(f"\n💾 Testing separate Excel file creation...")
    
    # Create separate data structures for each card
    property_overview_data = []
    sale_rental_data = []
    household_data = []
    additional_info_data = []
    natural_risks_data = []
    schools_data = []
    valuation_data = []
    property_history_data = []
    
    for prop in all_property_data:
        # Property Overview Card
        property_overview_data.append({
            'Property_URL': prop.get('Property_URL', ''),
            'Address': prop.get('Address', ''),
            'Property_Type': prop.get('Property_Type', ''),
            'Land_Size': prop.get('Land_Size', ''),
            'Floor_Area': prop.get('Floor_Area', ''),
            'Bedrooms': prop.get('Bedrooms', ''),
            'Bathrooms': prop.get('Bathrooms', ''),
            'Car_Spaces': prop.get('Car_Spaces', ''),
            'Scraping_Date': prop.get('Scraping_Date', '')
        })
        
        # Sale/Rental Information Card
        sale_rental_data.append({
            'Property_URL': prop.get('Property_URL', ''),
            'Address': prop.get('Address', ''),
            'Last_Sold_Price': prop.get('Last_Sold_Price', ''),
            'Last_Sold_Date': prop.get('Last_Sold_Date', ''),
            'Sold_By': prop.get('Sold_By', ''),
            'Land_Use': prop.get('Land_Use', ''),
            'Issue_Date': prop.get('Issue_Date', ''),
            'Advertisement_Date': prop.get('Advertisement_Date', ''),
            'Listing_Description': prop.get('Listing_Description', ''),
            'Advertising_Agent_Info_JSON': prop.get('Advertising_Agent_Info_JSON', ''),
            'Sale_Information_JSON': prop.get('Sale_Information_JSON', ''),
            'Scraping_Date': prop.get('Scraping_Date', '')
        })
        
        # Household Information Card
        household_data.append({
            'Property_URL': prop.get('Property_URL', ''),
            'Address': prop.get('Address', ''),
            'Owner_Type': prop.get('Owner_Type', ''),
            'Current_Tenure': prop.get('Current_Tenure', ''),
            'Household_Information_Owner_Information': prop.get('Household_Information_Owner_Information', ''),
            'Household_Information_Marketing_Contacts': prop.get('Household_Information_Marketing_Contacts', ''),
            'Scraping_Date': prop.get('Scraping_Date', '')
        })
        
        # Additional Information Card
        additional_info_data.append({
            'Property_URL': prop.get('Property_URL', ''),
            'Address': prop.get('Address', ''),
            'Additional_Information_Legal_Description': prop.get('Additional_Information_Legal_Description', ''),
            'Additional_Information_Property_Features': prop.get('Additional_Information_Property_Features', ''),
            'Additional_Information_Land_Values': prop.get('Additional_Information_Land_Values', ''),
            'Scraping_Date': prop.get('Scraping_Date', '')
        })
        
        # Natural Risks Card
        natural_risks_data.append({
            'Property_URL': prop.get('Property_URL', ''),
            'Address': prop.get('Address', ''),
            'Natural_Risks': prop.get('Natural_Risks', ''),
            'Natural_Risks_JSON': prop.get('Natural_Risks_JSON', ''),
            'Scraping_Date': prop.get('Scraping_Date', '')
        })
        
        # Schools Card
        schools_data.append({
            'Property_URL': prop.get('Property_URL', ''),
            'Address': prop.get('Address', ''),
            'Nearby_Schools_In_Catchment': prop.get('Nearby_Schools_In_Catchment', ''),
            'Nearby_Schools_All_Nearby': prop.get('Nearby_Schools_All_Nearby', ''),
            'Scraping_Date': prop.get('Scraping_Date', '')
        })
        
        # Valuation Estimates Card
        valuation_data.append({
            'Property_URL': prop.get('Property_URL', ''),
            'Address': prop.get('Address', ''),
            'Valuation_Estimate_Estimate': prop.get('Valuation_Estimate_Estimate', ''),
            'Valuation_Estimate_Estimate_JSON': prop.get('Valuation_Estimate_Estimate_JSON', ''),
            'Valuation_Estimate_Rental': prop.get('Valuation_Estimate_Rental', ''),
            'Valuation_Estimate_Rental_JSON': prop.get('Valuation_Estimate_Rental_JSON', ''),
            'Scraping_Date': prop.get('Scraping_Date', '')
        })
        
        # Property History Card
        property_history_data.append({
            'Property_URL': prop.get('Property_URL', ''),
            'Address': prop.get('Address', ''),
            'Property_History_All': prop.get('Property_History_All', ''),
            'Property_History_Sale': prop.get('Property_History_Sale', ''),
            'Property_History_Listing': prop.get('Property_History_Listing', ''),
            'Property_History_Rental': prop.get('Property_History_Rental', ''),
            'Property_History_DA': prop.get('Property_History_DA', ''),
            'Properties_Sold_12_Months': prop.get('Properties_Sold_12_Months', ''),
            'Scraping_Date': prop.get('Scraping_Date', '')
        })
    
    # Save each card type to separate Excel files
    card_files = {
        'Property_Overview': property_overview_data,
        'Sale_Rental_Info': sale_rental_data,
        'Household_Info': household_data,
        'Additional_Info': additional_info_data,
        'Natural_Risks': natural_risks_data,
        'Schools': schools_data,
        'Valuation_Estimates': valuation_data,
        'Property_History': property_history_data
    }
    
    for card_name, card_data in card_files.items():
        if card_data:
            df_card = pd.DataFrame(card_data)
            filename = f'test_{card_name.lower()}.xlsx'
            df_card.to_excel(filename, index=False)
            print(f"✅ Test saved {len(card_data)} records to {filename}")
    
    # Also save a master file with all data for reference
    df_all = pd.DataFrame(all_property_data)
    df_all.to_excel('test_master.xlsx', index=False)
    print(f"✅ Test saved master file with all data to test_master.xlsx")
    
    print(f"\n📊 Test Summary:")
    print(f"  - Total properties processed: {len(all_property_data)}")
    print(f"  - Card-specific files created: {len(card_files)}")
    print(f"  - Master file created: test_master.xlsx")

def test_first_url():
    """Test function to debug the first URL specifically"""
    print("🧪 Testing first URL specifically...")
    
    # Read the CSV file with property URLs
    try:
        # df_links = pd.read_csv('vic_links.csv')
        # urls = df_links['Property_URL'].dropna().tolist()
        urls=['https://rpp.corelogic.com.au/property/47-wellington-parade-south-east-melbourne-vic-3002/17241185']
        first_url = urls[0] if urls else None
        print(f"📋 First URL: {first_url}")
    except Exception as e:
        print(f"❌ Error reading vic_links.csv: {e}")
        return
    
    # Setup Chrome driver
    options = Options()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(600)
    driver.set_script_timeout(600)
    
    try:
        # Login first
        print("🔐 Starting login process...")
        driver.get("https://rpp.corelogic.com.au/")
        print("✅ Login page loaded")
        
        # Wait for page to fully load
        time.sleep(29)
        
        # Check if we're already logged in
        try:
            current_url = driver.current_url
            print(f"Current URL after login page load: {current_url}")
            
            # If we're redirected to a different page, we might already be logged in
            if "login" not in current_url.lower() and "signin" not in current_url.lower():
                print("✅ Already logged in or redirected to main page")
            else:
                print("🔐 Proceeding with login...")
                
                username_field = wait_until_present(driver, By.ID, "username", timeout=10)
                username_field.clear()
                username_field.send_keys("delpg2021")
                print("✅ Username entered")
                
                password_field = wait_until_present(driver, By.ID, "password", timeout=10)
                password_field.clear()
                password_field.send_keys("FlatHead@2024")
                print("✅ Password entered")
                
                sign_on_button = wait_until_clickable(driver, By.ID, "signOnButton", timeout=10)
                sign_on_button.click()
                print("✅ Login button clicked")
                
                # Wait for login to complete and check for redirect
                time.sleep(30)
                current_url = driver.current_url
                print(f"URL after login attempt: {current_url}")
                
        except Exception as login_error:
            print(f"⚠️ Login error: {login_error}")
            print("Continuing anyway...")
        
        # Final wait to ensure we're ready
        time.sleep(3)
        
        # Test the first URL
        if first_url:
            print(f"\n🧪 Testing first URL: {first_url}")
            property_data = extract_property_data(driver, first_url)
            if property_data:
                print("✅ First URL test successful!")
                print(f"Address: {property_data.get('Address', 'N/A')}")
                
                # Test saving to separate Excel files
                print("\n💾 Testing separate Excel file creation...")
                test_save_separate_files([property_data])
            else:
                print("❌ First URL test failed!")
        else:
            print("❌ No URLs found in CSV")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        input("Press Enter to close browser...")  # Keep browser open for inspection
        driver.quit()
        print("🔚 Browser closed")

if __name__ == "__main__":
    # Uncomment the line below to test only the first URL
    # test_first_url()
    
    # Uncomment the line below to run full scraping
    scrape_all_properties()
