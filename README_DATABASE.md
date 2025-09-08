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
- **natural_risks** - Risk assessment data
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

#### Get Properties with Natural Risks:
```sql
SELECT p.address, p.property_type, nr.risk_type, nr.risk_status
FROM properties p
JOIN natural_risks nr ON p.id = nr.property_id
WHERE nr.risk_status = 'Detected';
```

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

```python
# Get property by URL
@app.get("/api/properties/{property_url}")
def get_property(property_url: str):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("CALL GetPropertyComplete(%s)", (property_url,))
    result = cursor.fetchone()
    return result

# Search properties
@app.get("/api/properties/search")
def search_properties(
    address: str = None,
    property_type: str = None,
    min_price: float = None,
    max_price: float = None,
    limit: int = 50
):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.callproc("SearchProperties", (address, property_type, min_price, max_price, limit))
    results = cursor.fetchall()
    return results

# Get statistics
@app.get("/api/statistics")
def get_statistics():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.callproc("GetScrapingStats")
    result = cursor.fetchone()
    return result
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
