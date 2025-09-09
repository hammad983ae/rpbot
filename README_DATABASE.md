# Property Data Scraping - Database Version

This version stores scraped property data in a MySQL database instead of Excel files, providing a professional structure for frontend applications.

## 🗄️ Database Setup

### 1. Install MySQL

Make sure you have MySQL installed and running on your system.

### 2. Create Database

```sql
CREATE DATABASE property_data;
USE property_data;
```

### 3. Run Schema Script

Execute the `property_database_schema.sql` file to create all tables, views, and procedures:

```bash
mysql -u your_username -p property_data < property_database_schema.sql
```

## 🔧 Configuration

### 1. Update Database Configuration

Edit `sales_scraping_db.py` and update the `DB_CONFIG` dictionary:

```python
DB_CONFIG = {
    'host': 'localhost',  # Your database host
    'database': 'property_data',  # Your database name
    'user': 'your_username',  # Your database username
    'password': 'your_password',  # Your database password
    'port': 3306,  # Your database port
    'charset': 'utf8mb4',
    'autocommit': True
}
```

### 2. Install Dependencies

```bash
pip install -r requirements_db.txt
```

## 🚀 Usage

### Run the Scraper

```bash
python sales_scraping_db.py
```

## 📊 Database Structure

### Main Tables:

- **properties** - Core property information
- **sale_rental_info** - Sale and rental details
- **household_info** - Owner and household information
- **additional_info** - Legal, features, and land values
- **nearby_schools** - School information
- **valuation_estimates** - Property and rental valuations
- **property_history** - Historical events
- **property_attributes** - JSON attributes
- **scraping_logs** - Monitoring and debugging

### Views:

- **property_complete_view** - Complete property data with all related information

### Stored Procedures:

- **GetPropertyComplete(property_url)** - Get complete property data
- **SearchProperties(address, type, min_price, max_price, limit)** - Search properties
- **GetScrapingStats()** - Get scraping statistics

## 🔍 Frontend Integration

### Example Queries:

#### Get Complete Property Data:

```sql
SELECT * FROM property_complete_view WHERE property_url = 'your_property_url';
```

#### Search Properties:

```sql
CALL SearchProperties('Melbourne', 'House', 500000, 2000000, 50);
```

#### Get Scraping Statistics:

```sql
CALL GetScrapingStats();
```

<!-- Natural risks feature removed -->

#### Get Properties with School Information:

```sql
SELECT p.address, COUNT(ns.id) as school_count
FROM properties p
LEFT JOIN nearby_schools ns ON p.id = ns.property_id
WHERE ns.catchment_status = 'In Catchment'
GROUP BY p.id, p.address;
```

## 📈 Performance Features

### Indexes:

- All foreign keys have indexes
- Composite indexes for common query patterns
- Optimized for frontend queries

### Data Validation:

- Triggers for URL format validation
- Automatic numeric value conversion
- Data integrity constraints

### Monitoring:

- Scraping logs table for monitoring
- Performance tracking
- Error logging

## 🔧 API Integration Examples

### REST API Endpoints (using Flask/FastAPI):

### POST /scrape-property

Scrape a property by address and return sanitized, frontend-friendly JSON.

Notes:

- The first autocomplete suggestion is selected only if its similarity to the input address is at least 0.90. Otherwise the request aborts with an error.

Request:

```http
POST /scrape-property
Content-Type: application/json

{
  "address": "200 George Street Sydney NSW 2000"
}
```

Response 200:

```json
{
  "success": true,
  "message": "Property data scraped and saved successfully",
  "data": {
    "id": 123,
    "propertyUrl": "https://rpp.corelogic.com.au/property/47-wellington-parade-south-east-melbourne-vic-3002/17241185",
    "address": "200 George Street, Sydney NSW 2000",
    "type": "House",
    "bedrooms": "3",
    "bathrooms": "2",
    "carSpaces": "1",
    "landSize": "512 m²",
    "floorArea": "128 m²",
    "lastSold": { "price": "$1,250,000", "date": "14 Feb 2023", "soldBy": "Acme Realty" },
    "sale": {
      "landUse": "Residential",
      "issueDate": "03 Mar 2021",
      "advertisementDate": "10 Jan 2023",
      "listingDescription": "Beautifully renovated period home featuring 3 bedrooms, 2 bathrooms, off-street parking, and a landscaped garden within walking distance to Fitzroy Gardens."
    },
    "agent": { "agency": "ABC Realty", "name": "Jane Doe", "phone": "+61 412 345 678" },
    "additional": {
      "legalDescription": { "RPD": "CROWN LOT 5 SEC 19B:PH MELBOURNE NORTH", "Vol/Fol": "Withheld", "Title Indicator": "No More Titles", "LA": "Melbourne", "Issue Date": "2312", "Ref Sec": "19B", "Heritage Area": "True" },
      "features": { "Floor Area": "192", "Property Improvements": "Brick" },
      "landValues": "Not available"
    },
    "household": { "ownerType": "Owner Occupied", "currentTenure": "Freehold" },
    "valuation": {
      "estimate": "Low: $1,180,000 | Estimate: $1,250,000 | High: $1,320,000 | Confidence: High",
      "estimateJson": {"confidence":"High","low_value":"$1,180,000","estimate_value":"$1,250,000","high_value":"$1,320,000"},
      "rental": "Low: $750/week | Estimate: $820/week | High: $890/week | Yield: 3.4% | Confidence: Medium",
      "rentalJson": {"confidence":"Medium","low_value":"$750/week","estimate_value":"$820/week","high_value":"$890/week","rental_yield":"3.4%"}
    },
    "schools": {
      "inCatchment": [{"name":"Richmond West Primary School","address":"23 Lennox Street Richmond VIC 3121","distance":"0.82 km","attributes":{"type":"PRIMARY","sector":"GOVERNMENT","gender":"MIXED","year_levels":"","enrollments":""}}, {"name":"Richmond High School","address":"","distance":"1.3 km","attributes":{"type":"SECONDARY","sector":"GOVERNMENT","gender":"MIXED","year_levels":"","enrollments":""}}],
      "allNearby": [{"name":"Richmond West Primary School","address":"23 Lennox Street Richmond VIC 3121","distance":"0.82 km","attributes":{"type":"PRIMARY","sector":"GOVERNMENT","gender":"MIXED","year_levels":"","enrollments":""}}, {"name":"Melbourne Indigenous Transition School","address":"","distance":"0.88 km","attributes":{"type":"SPECIAL","sector":"NON-GOVERNMENT","gender":"MIXED","year_levels":"","enrollments":""}}]
    },
    "scrapedAt": "2025-09-09 12:34:56"
  }
}
```

Errors:

```json
{ "success": false, "message": "Address is required" }
```


## 🛠️ Maintenance

### Backup Database:

```bash
mysqldump -u your_username -p property_data > property_data_backup.sql
```

### Monitor Scraping:

```sql
SELECT 
    scraping_status,
    COUNT(*) as count,
    AVG(scraping_duration_seconds) as avg_duration
FROM scraping_logs 
WHERE scraped_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
GROUP BY scraping_status;
```

### Clean Old Data:

```sql
-- Delete scraping logs older than 30 days
DELETE FROM scraping_logs WHERE scraped_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- Delete properties with no related data (optional)
DELETE p FROM properties p 
LEFT JOIN sale_rental_info sri ON p.id = sri.property_id
WHERE sri.property_id IS NULL;
```

## 🔒 Security Considerations

1. **Use Environment Variables** for database credentials
2. **Implement Connection Pooling** for production
3. **Add SSL/TLS** for remote connections
4. **Regular Backups** of your database
5. **Monitor Access Logs** for suspicious activity

## 📝 Notes

- The database schema is designed for scalability and performance
- JSON fields provide flexibility for future data structure changes
- Views and stored procedures simplify frontend integration
- Comprehensive logging helps with debugging and monitoring
- The structure supports both simple queries and complex analytics
