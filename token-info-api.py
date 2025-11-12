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
    
    # Extract token name
    # There can be many divs with class 'chakra-stack'. We want the one
    # that contains an h2.chakra-heading > span (token name).
    name_elem = None
    candidates = []
    for div in soup.find_all('div', class_='chakra-stack'):
        h2 = div.find('h2', class_='chakra-heading')
        if not h2:
            continue
        span = h2.find('span')
        if not span:
            continue
        text = span.get_text(strip=True)
        if not text:
            continue
        # Heuristics: ignore overly long strings and ones with whitespace-only
        if 1 <= len(text) <= 80:
            candidates.append((div, span, text))

    # Prefer a candidate that also sits close to a known logo_img ancestor
    chosen_text = None
    if candidates:
        if logo_img:
            # Walk up parents of logo_img to find a chakra-stack container
            logo_anc = None
            parent = logo_img.parent
            while parent is not None:
                if getattr(parent, 'name', None) == 'div' and 'chakra-stack' in parent.get('class', []):
                    logo_anc = parent
                    break
                parent = getattr(parent, 'parent', None)

            if logo_anc is not None:
                # Choose the first candidate under the same chakra-stack ancestor
                for div, span, text in candidates:
                    if div is logo_anc or logo_anc in div.parents:
                        chosen_text = text
                        break

        # Fallback: choose the first reasonable candidate
        if not chosen_text:
            chosen_text = candidates[0][2]

    if chosen_text:
        dprint(f"Token Name (chosen): {chosen_text}")
    else:
        dprint("Token Name not found via structured pattern")
    
    token_data = {
        'contract': addr.split('/')[-1],  
        'name': chosen_text if chosen_text else 'Unknown',
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
            'logo_url': result['thumbnail'],
            'name': result['name']
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
                INSERT INTO tokens (contract, name, thumbnail)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    thumbnail = VALUES(thumbnail)
            """, (token_data['contract'], token_data['name'], token_data['logo_url']))
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