-- =============================================
-- DATABASE SETUP
-- =============================================

-- Create database (run separately if not exists)
-- CREATE DATABASE property_data;
-- \c property_data

-- =============================================
-- ENUM TYPES
-- =============================================
-- Enable trigram similarity for fuzzy address matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE TYPE catchment_enum AS ENUM ('In Catchment', 'All Nearby');
CREATE TYPE estimate_enum AS ENUM ('Property Valuation', 'Rental Estimate');
CREATE TYPE history_enum AS ENUM ('All', 'Sale', 'Listing', 'Rental', 'DA');
CREATE TYPE scraping_status_enum AS ENUM ('Success', 'Failed', 'Partial');

-- =============================================
-- MAIN PROPERTIES TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS properties (
    id SERIAL PRIMARY KEY,
    property_url VARCHAR(500) NOT NULL UNIQUE,
    address VARCHAR(255) NOT NULL,
    property_type VARCHAR(100),
    land_size VARCHAR(50),
    floor_area VARCHAR(50),
    bedrooms VARCHAR(10),
    bathrooms VARCHAR(10),
    car_spaces VARCHAR(10),
    scraping_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_address ON properties(address);
CREATE INDEX idx_property_type ON properties(property_type);
CREATE INDEX idx_scraping_date ON properties(scraping_date);
-- Trigram index to accelerate similarity() and % operator on address
CREATE INDEX IF NOT EXISTS idx_properties_address_trgm ON properties USING gin (address gin_trgm_ops);

-- =============================================
-- SALE & RENTAL INFORMATION
-- =============================================
CREATE TABLE IF NOT EXISTS sale_rental_info (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL,
    last_sold_price VARCHAR(50),
    last_sold_date VARCHAR(100),
    sold_by VARCHAR(255),
    land_use VARCHAR(100),
    issue_date VARCHAR(100),
    advertisement_date VARCHAR(100),
    listing_description TEXT,
    advertising_agency VARCHAR(255),
    advertising_agent VARCHAR(255),
    agent_phone VARCHAR(50),
    sale_price_numeric DECIMAL(15,2),
    sale_date_parsed DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

CREATE INDEX idx_sale_price ON sale_rental_info(sale_price_numeric);
CREATE INDEX idx_sale_date ON sale_rental_info(sale_date_parsed);
CREATE INDEX idx_advertising_agency ON sale_rental_info(advertising_agency);

-- =============================================
-- HOUSEHOLD INFORMATION
-- =============================================
CREATE TABLE IF NOT EXISTS household_info (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL,
    owner_type VARCHAR(100),
    current_tenure VARCHAR(100),
    owner_information TEXT,
    marketing_contacts TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

-- =============================================
-- ADDITIONAL INFORMATION
-- =============================================
CREATE TABLE IF NOT EXISTS additional_info (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL,
    legal_description TEXT,
    property_features TEXT,
    land_values TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

-- Natural risks feature removed

-- =============================================
-- NEARBY SCHOOLS
-- =============================================
CREATE TABLE IF NOT EXISTS nearby_schools (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL,
    school_name VARCHAR(255) NOT NULL,
    school_address TEXT,
    distance VARCHAR(50),
    school_type VARCHAR(100),
    school_sector VARCHAR(100),
    school_gender VARCHAR(50),
    year_levels VARCHAR(100),
    enrollments VARCHAR(50),
    catchment_status catchment_enum NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

CREATE INDEX idx_school_name ON nearby_schools(school_name);
CREATE INDEX idx_catchment_status ON nearby_schools(catchment_status);
CREATE INDEX idx_school_type ON nearby_schools(school_type);

-- =============================================
-- VALUATION ESTIMATES
-- =============================================
CREATE TABLE IF NOT EXISTS valuation_estimates (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL,
    estimate_type estimate_enum NOT NULL,
    confidence_level VARCHAR(100),
    low_value VARCHAR(50),
    estimate_value VARCHAR(50),
    high_value VARCHAR(50),
    rental_yield VARCHAR(20),
    low_value_numeric DECIMAL(15,2),
    estimate_value_numeric DECIMAL(15,2),
    high_value_numeric DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

CREATE INDEX idx_estimate_type ON valuation_estimates(estimate_type);
CREATE INDEX idx_estimate_value ON valuation_estimates(estimate_value_numeric);

-- =============================================
-- PROPERTY HISTORY
-- =============================================
CREATE TABLE IF NOT EXISTS property_history (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL,
    history_type history_enum NOT NULL,
    event_date VARCHAR(100),
    event_description TEXT,
    event_details TEXT,
    properties_sold_12_months VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

CREATE INDEX idx_history_type ON property_history(history_type);
CREATE INDEX idx_event_date ON property_history(event_date);

-- =============================================
-- PROPERTY ATTRIBUTES
-- =============================================
CREATE TABLE IF NOT EXISTS property_attributes (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL,
    attributes_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

-- =============================================
-- SCRAPING LOGS
-- =============================================
CREATE TABLE IF NOT EXISTS scraping_logs (
    id SERIAL PRIMARY KEY,
    property_url VARCHAR(500) NOT NULL,
    scraping_status scraping_status_enum NOT NULL,
    error_message TEXT,
    scraping_duration_seconds INT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scraping_status ON scraping_logs(scraping_status);
CREATE INDEX idx_scraped_at ON scraping_logs(scraped_at);

-- =============================================
-- VIEWS
-- =============================================
CREATE OR REPLACE VIEW property_complete_view AS
SELECT 
    p.id,
    p.property_url,
    p.address,
    p.property_type,
    p.land_size,
    p.floor_area,
    p.bedrooms,
    p.bathrooms,
    p.car_spaces,
    p.scraping_date,

    -- Sale/Rental Info
    sri.last_sold_price,
    sri.last_sold_date,
    sri.sold_by,
    sri.advertising_agency,
    sri.advertising_agent,
    sri.agent_phone,
    sri.sale_price_numeric,
    sri.sale_date_parsed,

    -- Household Info
    hi.owner_type,
    hi.current_tenure,

    -- Additional Info
    ai.legal_description,
    ai.property_features,
    ai.land_values,

    -- Natural risks summary removed

    -- Schools Count
    (SELECT COUNT(*) FROM nearby_schools ns WHERE ns.property_id = p.id AND ns.catchment_status = 'In Catchment') as schools_in_catchment_count,
    (SELECT COUNT(*) FROM nearby_schools ns WHERE ns.property_id = p.id AND ns.catchment_status = 'All Nearby') as schools_nearby_count,

    -- Valuation Estimates
    (SELECT ve.estimate_value FROM valuation_estimates ve WHERE ve.property_id = p.id AND ve.estimate_type = 'Property Valuation' LIMIT 1) as property_valuation,
    (SELECT ve.estimate_value FROM valuation_estimates ve WHERE ve.property_id = p.id AND ve.estimate_type = 'Rental Estimate' LIMIT 1) as rental_estimate,

    -- Property History Count
    (SELECT COUNT(*) FROM property_history ph WHERE ph.property_id = p.id) as history_events_count,

    p.created_at,
    p.updated_at

FROM properties p
LEFT JOIN sale_rental_info sri ON p.id = sri.property_id
LEFT JOIN household_info hi ON p.id = hi.property_id
LEFT JOIN additional_info ai ON p.id = ai.property_id;

-- =============================================
-- FUNCTIONS
-- =============================================
-- Returns the most similar property to the provided address using trigram similarity
CREATE OR REPLACE FUNCTION GetMostSimilarProperty(address_query TEXT, min_sim NUMERIC DEFAULT 0.0)
RETURNS TABLE (
    id INT,
    property_url VARCHAR,
    address VARCHAR,
    similarity NUMERIC
)
LANGUAGE sql AS $$
    SELECT p.id, p.property_url, p.address, similarity(p.address, address_query) AS similarity
    FROM properties p
    WHERE similarity(p.address, address_query) >= min_sim
    ORDER BY similarity DESC
    LIMIT 1
$$;
CREATE OR REPLACE FUNCTION GetPropertyComplete(property_url_param VARCHAR)
RETURNS SETOF property_complete_view
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM property_complete_view WHERE property_url = property_url_param;
END;
$$;

CREATE OR REPLACE FUNCTION SearchProperties(
    address_search VARCHAR,
    property_type_filter VARCHAR,
    min_price DECIMAL,
    max_price DECIMAL,
    limit_count INT
)
RETURNS SETOF property_complete_view
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT * 
    FROM property_complete_view 
    WHERE (address_search IS NULL OR address ILIKE '%' || address_search || '%')
      AND (property_type_filter IS NULL OR property_type = property_type_filter)
      AND (min_price IS NULL OR sale_price_numeric >= min_price)
      AND (max_price IS NULL OR sale_price_numeric <= max_price)
    ORDER BY scraping_date DESC
    LIMIT COALESCE(limit_count, 50);
END;
$$;

CREATE OR REPLACE FUNCTION GetScrapingStats()
RETURNS TABLE (
    total_properties BIGINT,
    scraped_last_24h BIGINT,
    scraped_last_7d BIGINT,
    avg_sale_price NUMERIC,
    min_sale_price NUMERIC,
    max_sale_price NUMERIC
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_properties,
        COUNT(*) FILTER (WHERE scraping_date >= NOW() - INTERVAL '1 day') as scraped_last_24h,
        COUNT(*) FILTER (WHERE scraping_date >= NOW() - INTERVAL '7 days') as scraped_last_7d,
        AVG(sri.sale_price_numeric) as avg_sale_price,
        MIN(sri.sale_price_numeric) as min_sale_price,
        MAX(sri.sale_price_numeric) as max_sale_price
    FROM properties p
    LEFT JOIN sale_rental_info sri ON p.id = sri.property_id;
END;
$$;

-- =============================================
-- TRIGGERS
-- =============================================
CREATE OR REPLACE FUNCTION validate_property_url()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.property_url NOT LIKE 'https://rpp.corelogic.com.au/property/%' THEN
        RAISE EXCEPTION 'Invalid property URL format: %', NEW.property_url;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_property_url_trigger
BEFORE INSERT ON properties
FOR EACH ROW
EXECUTE FUNCTION validate_property_url();

CREATE OR REPLACE FUNCTION update_sale_price_numeric()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.last_sold_price IS NOT NULL THEN
        NEW.sale_price_numeric := 
            REPLACE(REPLACE(NEW.last_sold_price, '$', ''), ',', '')::DECIMAL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_sale_price_numeric_trigger
BEFORE INSERT OR UPDATE ON sale_rental_info
FOR EACH ROW
EXECUTE FUNCTION update_sale_price_numeric();
