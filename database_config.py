# Database Configuration
# Update these values with your actual database connection details

DB_CONFIG = {
    'host': 'localhost',  # Your database host (e.g., 'localhost', '127.0.0.1', or remote host)
    'database': 'property_data',  # Your database name
    'user': 'your_username',  # Your database username
    'password': 'your_password',  # Your database password
    'port': 3306,  # Your database port (default MySQL port is 3306)
    'charset': 'utf8mb4',
    'autocommit': True,
    'use_unicode': True,
    'sql_mode': 'TRADITIONAL'
}

# Example configurations for different environments:

# Local MySQL
LOCAL_CONFIG = {
    'host': 'localhost',
    'database': 'property_data',
    'user': 'root',
    'password': 'your_password',
    'port': 3306,
    'charset': 'utf8mb4',
    'autocommit': True
}

# Remote MySQL
REMOTE_CONFIG = {
    'host': 'your-remote-host.com',
    'database': 'property_data',
    'user': 'your_username',
    'password': 'your_password',
    'port': 3306,
    'charset': 'utf8mb4',
    'autocommit': True
}

# Cloud MySQL (e.g., AWS RDS, Google Cloud SQL)
CLOUD_CONFIG = {
    'host': 'your-cloud-instance.region.rds.amazonaws.com',
    'database': 'property_data',
    'user': 'admin',
    'password': 'your_secure_password',
    'port': 3306,
    'charset': 'utf8mb4',
    'autocommit': True
}

# To use a specific configuration, update the DB_CONFIG in sales_scraping_db.py:
# DB_CONFIG = LOCAL_CONFIG  # or REMOTE_CONFIG, CLOUD_CONFIG
