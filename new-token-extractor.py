from seleniumbase import SB # Import SeleniumBase
from bs4 import BeautifulSoup
import regex # type: ignore # Using regex library
from concurrent.futures import ProcessPoolExecutor, as_completed
import threading
import mysql.connector  # type: ignore

target_url = "https://dexscreener.com/solana?rankBy=trendingScoreH24&order=desc"
sqldb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
)

DEBUG_PRINT = True  # Set to True for debugging output

def debug_print(message):
    if DEBUG_PRINT:
        thread = threading.current_thread()
        thread_info = f"[{thread.name} | ID: {thread.ident}]"
        print(f"{thread_info}  :: {message}")  

# --- Main Execution ---
if __name__ == "__main__":
    sql_cursor = sqldb.cursor()
    sql_cursor.execute("CREATE DATABASE IF NOT EXISTS solana_tokens")
    sql_cursor.execute("USE solana_tokens")
    sql_cursor.execute("""
        CREATE TABLE IF NOT EXISTS treanding_tokens (
            address VARCHAR(44) PRIMARY KEY,
            name VARCHAR(255),
            market_cap VARCHAR(50),
            liquidity VARCHAR(50),
            volume VARCHAR(50)
        )
    """)
    sql_cursor.execute("""
        CREATE TABLE IF NOT EXISTS traders (
            wallet_address VARCHAR(44) PRIMARY KEY,
            token_address VARCHAR(44),
            FOREIGN KEY (token_address) REFERENCES treanding_tokens(address)
        )
                       """)
    sqldb.commit()
    
    debug_print(f"Attempting to scrape with SeleniumBase: {target_url}")

    while True:
        try:
            # Use SB context manager for automatic driver management and UC mode
            # uc=True enables undetected-chromedriver features
            # test=True can sometimes help with stability/configuration
            # locale_code sets browser language, potentially aiding bypass
            with SB(uc=True, test=True, locale_code="en", headless=True) as sb: # headless=True runs without visible browser
                debug_print("Setting up SeleniumBase driver (uc mode)...")

                # activate_cdp_mode often used with uc=True for better interaction & navigation
                debug_print(f"Navigating to {target_url} using CDP mode...")
                sb.activate_cdp_mode(target_url)

                # Short wait for the potential verification page to appear
                debug_print(f"Waiting {4}s before potential captcha click...")
                sb.sleep(4)

                # Attempt to click the Cloudflare checkbox IF it appears visually
                # SeleniumBase tries to handle this automatically, but this adds robustness
                debug_print("Attempting uc_gui_click_captcha() (may not be needed if bypassed automatically)...")
                try:
                    sb.uc_gui_click_captcha()
                    debug_print("uc_gui_click_captcha executed.")
                except Exception as captcha_click_error:
                    debug_print(f"Captcha click failed or wasn't necessary: {captcha_click_error}")
                
                # wait until the token image elements load 
                debug_print("Waiting for the token image elements to load...")
                sb.wait_for_element_visible('img.ds-dex-table-row-token-icon-img', timeout=50)
                debug_print("Token image elements are now visible.")

                debug_print("Getting page source after potential bypass...")
                debug_print("Getting page source after potential bypass...")
                page_source = sb.get_page_source()

                debug_print("Parsing HTML with BeautifulSoup...")
                soup = BeautifulSoup(page_source, 'html.parser')

                # --- Extraction Logic (same as before) ---
                token_icon_imgs = soup.find_all('img', class_='ds-dex-table-row-token-icon-img')

                if token_icon_imgs:
                    debug_print(f"Found {len(token_icon_imgs)} potential token images. Extracting addresses...")

                    solana_address_pattern = regex.compile(r'/solana/([1-9A-HJ-NP-Za-km-z]{32,44})\.(?:png|jpg|jpeg|gif|webp)', regex.IGNORECASE)

                    for img in token_icon_imgs:
                        if img and 'src' in img.attrs:
                            # Extract the src attribute from the image tag
                            src = img['src']
                            match = solana_address_pattern.search(src)
                            if match:
                                token_address = match.group(1)
                                if 32 <= len(token_address) <= 44:
                                    #get the each token name
                                    token_name = img.find_next('span', class_='ds-dex-table-row-base-token-name-text').text.strip()
                                    
                                    # get the each token market cap, liquidity, and volume
                                    market_cap = img.find_next('div', class_='ds-dex-table-row-col-market-cap').text.strip()
                                    liquidity = img.find_next('div', class_='ds-dex-table-row-col-liquidity').text.strip()
                                    volume = img.find_next('div', class_='ds-dex-table-row-col-volume').text.strip()
                                    link_to_token = f"https://dexscreener.com/solana/{token_address}"
                                    
                                    # create a dictionary for each token
                                    token_info = {
                                        'address': token_address,
                                        'name': token_name,
                                        'market_cap': market_cap,
                                        'liquidity': liquidity,
                                        'volume': volume,
                                        'link': link_to_token
                                    }
                                    
                                    debug_print(f"Found token: {token_name} at {token_address} with market cap {market_cap}, liquidity {liquidity}, volume {volume}. Link: {link_to_token}")
                                    # save to database
                                    try:
                                        sql_cursor.execute("""
                                            INSERT INTO treanding_tokens (address, name, market_cap, liquidity, volume)
                                            VALUES (%s, %s, %s, %s, %s)
                                            ON DUPLICATE KEY UPDATE   
                                                name = VALUES(name),
                                                market_cap = VALUES(market_cap),
                                                liquidity = VALUES(liquidity),
                                                volume = VALUES(volume)
                                        """, (token_address, token_name, market_cap, liquidity, volume))
                                        sqldb.commit()
                                        debug_print(f"Token {token_address} saved to database.")
                                    except mysql.connector.Error as err:
                                        debug_print(f"Error saving token {token_address} to database: {err}")
                                    
                                else:
                                    debug_print(f"  - Possible invalid length found: {token_address} in {src}")

        except Exception as e:
            debug_print(f"An error occurred during SeleniumBase scraping: {e}")
            # Consider adding sb.save_screenshot_to_logs() here too on error
            # delay before retrying
            debug_print("Retrying in 10 seconds...")
            sb.sleep(10)
            continue
        
    # finally:
    #     # Ensure the database connection is closed
    #     if sql_cursor:
    #         sql_cursor.close()
    #     if sqldb.is_connected():
    #         sqldb.close()
    #     debug_print("Database connection closed.")