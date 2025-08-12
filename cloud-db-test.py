import mysql.connector
import urllib.parse
import os

# Use environment variable for database URL
db_url = os.getenv("AIVEN_DATABASE_URL", "mysql://user:password@host:port/database")
url = urllib.parse.urlparse(db_url)
conn = mysql.connector.connect(
    host=url.hostname,
    port=url.port,
    user=url.username,
    password=url.password,
    database=url.path.lstrip("/"),
    ssl_disabled=False
)
print("Connected:", conn.is_connected())
conn.close()