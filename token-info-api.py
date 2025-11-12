import os
import json
import mysql.connector
import re
from flask import Flask, jsonify
from seleniumbase import SB
import urllib.parse
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

app = Flask(__name__)

# Environment variables
db_url = os.getenv("DB_URL")  # Set this in your .env file

if not db_url:
    raise RuntimeError("DB_URL environment variable is required")

url = urllib.parse.urlparse(db_url)

sqldb = mysql.connector.connect(
    host=url.hostname,
    port=url.port,
    user=url.username,
    password=url.password,
    database=url.path.lstrip("/"),
    ssl_disabled=False,
    autocommit=True
)

HEADLESS = os.getenv("HEADLESS", "1") == "1"

def dprint(message):
    print(f"API:: {message}")

def scrape_token_info(addr: str) -> dict:
    with SB(uc=True, test=True, locale_code="en", headless=HEADLESS) as sb:
        dprint(f"Navigate: {addr}")
        sb.activate_cdp_mode(addr)
        sb.sleep(1)
        try: sb.uc_gui_click_captcha()
        except Exception as e: dprint(f"Captcha not present/ignored: {e}")
        sb.sleep(1)
        html = sb.get_page_source()

    soup = BeautifulSoup(html, "html.parser")
    
    # Find the logo image URL using BeautifulSoup
    logo_img = soup.find('img', src=re.compile(r'cdn\.dexscreener\.com/cms/images/'))
    logo_url = logo_img['src'] if logo_img else None
    
    token_data = {
        'contract': addr.split('/')[-1],  
        'logo_url': logo_url
    }
    
    return token_data


@app.route('/token/<token_address>', methods=['GET'])
def get_token_info(token_address: str):
    # Check if token exists in DB
    cursor = sqldb.cursor(dictionary=True, buffered=True)
    cursor.execute("USE solana_tokens")
    cursor.execute("SELECT * FROM tokens WHERE contract = %s", (token_address,))
    result = cursor.fetchone()
    cursor.close()

    if result:
        token_data = {
            'contract': result['contract'],
            'logo_url': result['thumbnail']
        }
        return jsonify(token_data)
    else:
        # Scrape from dexscreener
        addr = f"https://dexscreener.com/solana/{token_address}"
        token_data = scrape_token_info(addr)
        
        if token_data:
            # Insert into DB
            cursor = sqldb.cursor(buffered=True)
            cursor.execute("USE solana_tokens")
            cursor.execute("""
                INSERT INTO tokens (contract, thumbnail)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE
                    thumbnail = VALUES(thumbnail)
            """, (token_data['contract'],  token_data['logo_url']))
            sqldb.commit()
            cursor.close()
            return jsonify(token_data)
        else:
            return jsonify({"error": "Failed to scrape token data"}), 500



if __name__ == "__main__":
    # Use tokens table in solana_tokens DB
    try:
        sql_cursor = sqldb.cursor(buffered=True)
        sql_cursor.execute("USE solana_tokens")
        sql_cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                id INT AUTO_INCREMENT PRIMARY KEY,
                chain VARCHAR(10),
                contract VARCHAR(64),
                name VARCHAR(255),
                market_cap DOUBLE,
                liquidity DOUBLE,
                volume DOUBLE,
                thumbnail VARCHAR(255)
            )
                    """)
        sqldb.commit()
        sql_cursor.close()
    except mysql.connector.Error as err:
        print(f"Error initializing MySQL: {err}")
        exit(1)

    app.run(host='0.0.0.0', port=5000, debug=True)