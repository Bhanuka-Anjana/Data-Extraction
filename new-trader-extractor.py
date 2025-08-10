# pip install seleniumbase beautifulsoup4 requests regex
from seleniumbase import SB # Import SeleniumBase
from bs4 import BeautifulSoup
import regex # Using regex library
from concurrent.futures import ProcessPoolExecutor, as_completed
import threading
import mysql.connector 

number_of_threads = 5  # Number of threads to use for concurrent processing

sqldb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="solana_tokens"
)

sql_cursor = sqldb.cursor()

DEBUG_PRINT = True  # Set to True for debugging output

def debug_print(message):
    if DEBUG_PRINT:
        thread = threading.current_thread()
        thread_info = f"[{thread.name} | ID: {thread.ident}]"
        print(f"{thread_info}  :: {message}")

def parse_number(value_str):
    if not value_str:
        return None

    value_str = value_str.replace(",", "").strip().replace("$", "").replace("%", "")
    multiplier = 1.0

    if value_str.endswith("K"):
        multiplier = 1_000.0
        value_str = value_str[:-1]
    elif value_str.endswith("M"):
        multiplier = 1_000_000.0
        value_str = value_str[:-1]
    elif value_str.endswith("B"):
        multiplier = 1_000_000_000.0
        value_str = value_str[:-1]

    try:
        return float(value_str) * multiplier
    except ValueError:
        return None
        
def extract_traders_from_token(trending_tokens):    
    db_lock = threading.Lock()  # Lock for database operations

    if trending_tokens:
            debug_print(f"Found {len(trending_tokens)} trending tokens in the database.")
            for token in trending_tokens:
                debug_print(f"Processing token: {token[0]}")
                url = f"https://dexscreener.com/solana/{token[0]}"
                try:
                    # Use SB context manager for automatic driver management and UC mode
                    # uc=True enables undetected-chromedriver features
                    # test=True can sometimes help with stability/configuration
                    # locale_code sets browser language, potentially aiding bypass
                    with SB(uc=True, test=True, locale_code="en", headless=True) as sb: # headless=True runs without visible browser
                        debug_print("Setting up SeleniumBase driver (uc mode)...")

                        # activate_cdp_mode often used with uc=True for better interaction & navigation
                        debug_print(f"Navigating to {url} using CDP mode...")
                        sb.activate_cdp_mode(url)

                        # Short wait for the potential verification page to appear
                        debug_print(f"Waiting {5}s before potential captcha click...")
                        sb.sleep(5)

                        # Attempt to click the Cloudflare checkbox IF it appears visually
                        # SeleniumBase tries to handle this automatically, but this adds robustness
                        debug_print("Attempting uc_gui_click_captcha() (may not be needed if bypassed automatically)...")
                        try:
                            sb.uc_gui_click_captcha()
                            debug_print("uc_gui_click_captcha executed.")
                        except Exception as captcha_click_error:
                            debug_print(f"Captcha click failed or wasn't necessary: {captcha_click_error}")
                        
                        # wait until the class custom-1oq7u8k loads
                        try:
                            debug_print("Waiting for the class custom-1oq7u8k elements to load...")
                            sb.wait_for_element_visible('div.custom-1oq7u8k', timeout=100)
                            debug_print("Class custom-1oq7u8k elements are now visible.")
                        except Exception as e:
                            debug_print(f"Error waiting for class custom-1oq7u8k elements: {e}")
                            # exit if the elements are not found
                            break
                        
                        
                        # find the button with class 'custom-165cjlo' and click it
                        debug_print("Finding and clicking the 'Top Traders' button...")
                        try:
                            sb.click('button:contains("Top Traders")')
                            debug_print("Clicked 'Top Traders' button successfully.")
                            
                            # wait until class_='custom-1hhf88o' loads
                            try:
                                debug_print("Waiting for the trader address elements to load...")
                                sb.wait_for_element_visible('a.custom-1hhf88o', timeout=100)
                                debug_print("Trader address elements are now visible.")
                            except Exception as e:
                                debug_print(f"Error waiting for trader address elements: {e}")
                                # Consider adding sb.save_screenshot_to_logs() here too on error
                                break
                            
                            # extract the html of the page after clicking the button
                            page_source = sb.get_page_source()
                            soup = BeautifulSoup(page_source, 'html.parser')
                            
                            # find all the a tag with class 'ds-dex-table-row-trader-address'
                            trader_address_tags = soup.find_all('a', class_='custom-1hhf88o')
                            
                            # loop through the tags and extract the href attribute
                            for tag in trader_address_tags:
                                if tag and 'href' in tag.attrs:
                                    href = tag['href']
                                    # debug_print(f"Found href: {href}")
                                    # https://solscan.io/account/8Hw9X9UwBso7Sp2CFnEEeUGW8pGDj9wghc78ccWFZWpU get the last part of the href
                                    wallet_address = href.split('/')[-1]

                                    # get the trader's gross profit, win rate, wins, losses, etc.
                                    debug_print(f"Extracting trader details for wallet address: {wallet_address}")

                                    target_url = f"https://dexcheck.ai/app/wallet-analyzer/{wallet_address}"

                                    debug_print(f"Navigating to trader details URL: {target_url}")
                                    sb.open(target_url)

                                    # Short wait for the potential verification page to appear
                                    debug_print(f"Waiting {4}s before potential captcha click...")
                                    sb.sleep(2)

                                    # Attempt to click the Cloudflare checkbox IF it appears visually
                                    # SeleniumBase tries to handle this automatically, but this adds robustness
                                    debug_print("Attempting uc_gui_click_captcha() (may not be needed if bypassed automatically)...")
                                    try:
                                        sb.uc_gui_click_captcha()
                                        debug_print("uc_gui_click_captcha executed.")
                                    except Exception as captcha_click_error:
                                        debug_print(f"Captcha click failed or wasn't necessary: {captcha_click_error}")

                                    # wait until the element <h3 class="text-sm text-white/70"> is visible
                                    debug_print("Waiting for element to load...")
                                    sb.wait_for_element_visible('img.bg-brand-background-highlight', timeout=50)
                                    debug_print("Element is now visible.")

                                    debug_print("Getting page source after potential bypass...")
                                    page_source = sb.get_page_source()

                                    debug_print("Parsing HTML with BeautifulSoup...")
                                    soup = BeautifulSoup(page_source, 'html.parser')

                                    # --- Gross Profit ---
                                    gross_profit = soup.find('h3', string=regex.compile(r"Gross Profit", flags=regex.I))
                                    if gross_profit:
                                        gross_profit_value = gross_profit.find_next('p').text.strip()
                                        gross_profit_value = parse_number(gross_profit_value)
                                        if gross_profit_value is not None:
                                            debug_print(f"Gross Profit: {gross_profit_value}")

                                    # --- Win Rate ---
                                    win_rate = soup.find('h3', string=regex.compile(r"Win Rate", flags=regex.I))
                                    if win_rate:
                                        win_rate_value = win_rate.find_next('p').text.strip()
                                        win_rate_value = parse_number(win_rate_value)
                                        if win_rate_value is not None:
                                            debug_print(f"Win Rate: {win_rate_value}")

                                    # --- Wins and Losses ---
                                    win_count = soup.find('p', string=regex.compile(r"Win", flags=regex.I))
                                    if win_count:
                                        win_value = win_count.find_next('p').text.strip()
                                        win_value = parse_number(win_value)
                                        if win_value is not None:
                                            debug_print(f"Wins: {win_value}")
                                    loss_count = soup.find('p', string=regex.compile(r"Lose", flags=regex.I))
                                    if loss_count:
                                        loss_value = loss_count.find_next('p').text.strip()
                                        loss_value = parse_number(loss_value)
                                        if loss_value is not None:
                                            debug_print(f"Losses: {loss_value}")

                                    # --- Trade Volume, Trades, Avg Trade Size ---
                                    # Based on known layout order and heading structure
                                    trade_volume = soup.find('p', string=regex.compile(r"Trading Volume", flags=regex.I))
                                    if trade_volume:
                                        trade_volume_value = trade_volume.find_next('p').text.strip()
                                        trade_volume_value = parse_number(trade_volume_value)
                                        if trade_volume_value is not None:
                                            debug_print(f"Trade Volume: {trade_volume_value}")
                                    trades = soup.find('p', string=regex.compile(r"Trades", flags=regex.I))
                                    if trades:
                                        trades_value = trades.find_next('p').text.strip()
                                        trades_value = parse_number(trades_value)
                                        if trades_value is not None:
                                            debug_print(f"Trades: {trades_value}")
                                        debug_print(f"Trades: {trades_value}")
                                    avg_trade_size = soup.find('p', string=regex.compile(r"Avg. Trade Size", flags=regex.I))
                                    if avg_trade_size:
                                        avg_trade_size_value = avg_trade_size.find_next('p').text.strip()
                                        avg_trade_size_value = parse_number(avg_trade_size_value)
                                        if avg_trade_size_value is not None:
                                            debug_print(f"Avg. Trade Size: {avg_trade_size_value}")

                                    # check if the wallet address is already in the database
                                    with db_lock:
                                        try:
                                            sql_cursor.execute("SELECT * FROM traders WHERE wallet_address = %s", (wallet_address,))
                                            result = sql_cursor.fetchone()
                                            if result:
                                                debug_print(f"Trader wallet address {wallet_address} already exists in the database.")

                                                # Update existing trader's data
                                                sql_cursor.execute("""
                                                    UPDATE traders SET
                                                        token_address = %s, 
                                                        gross_profit = %s,
                                                        win_rate = %s,
                                                        wins = %s,
                                                        losses = %s,
                                                        trade_volume = %s,
                                                        trades = %s,
                                                        avg_trade_size = %s
                                                    WHERE wallet_address = %s
                                                """, (
                                                    token[0], 
                                                    gross_profit_value, 
                                                    win_rate_value, 
                                                    win_value, 
                                                    loss_value, 
                                                    trade_volume_value, 
                                                    trades_value, 
                                                    avg_trade_size_value,
                                                    wallet_address
                                                ))
                                                debug_print(f"Updated existing trader wallet address {wallet_address} in the database.")
                                            else:
                                                debug_print(f"Adding new trader wallet address {wallet_address} to the database.")
                                                # Insert new trader's data
                                                sql_cursor.execute("""
                                                    INSERT INTO traders (
                                                        wallet_address, 
                                                        token_address, 
                                                        gross_profit, 
                                                        win_rate, 
                                                        wins, 
                                                        losses, 
                                                        trade_volume, 
                                                        trades, 
                                                        avg_trade_size
                                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                                """, (
                                                    wallet_address,
                                                    token[0],
                                                    gross_profit_value,
                                                    win_rate_value,
                                                    win_value,
                                                    loss_value,
                                                    trade_volume_value,
                                                    trades_value,
                                                    avg_trade_size_value
                                                ))
                                            sqldb.commit()
                                            debug_print(f"Database operation for trader {wallet_address} completed successfully.")
                                        except mysql.connector.Error as db_err:
                                            debug_print(f"Database error for trader {wallet_address}: {db_err}")
                                            sqldb.rollback()
                                        except Exception as e:
                                            debug_print(f"Unexpected error for trader {wallet_address}: {e}")
                                            sqldb.rollback()

                        except Exception as e:
                            debug_print(f"Error clicking 'Top Traders' button: {e}")

                except Exception as e:
                    debug_print(f"An error occurred during SeleniumBase scraping: {e}")
                    # Consider adding sb.save_screenshot_to_logs() here too on error
            
# --- Main Execution ---
if __name__ == "__main__":    
    try:
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
                gross_profit DECIMAL(20, 2),
                win_rate DECIMAL(5, 2),
                wins INT,
                losses INT,
                trade_volume DECIMAL(20, 2),
                trades INT,
                avg_trade_size DECIMAL(20, 2),
                FOREIGN KEY (token_address) REFERENCES treanding_tokens(address)
            )
                        """)
        sqldb.commit()
        
        # get the list of trending tokens from the database
        sql_cursor.execute("SELECT address FROM treanding_tokens")
        trending_tokens = sql_cursor.fetchall()
        
        # divide the trending tokens into chunks for processing
        if trending_tokens:
            debug_print(f"Found {len(trending_tokens)} trending tokens in the database.")
            
            # Use ProcessPoolExecutor for concurrent processing
            with ProcessPoolExecutor(max_workers=number_of_threads) as executor:
                futures = []
                for i in range(0, len(trending_tokens), number_of_threads):
                    chunk = trending_tokens[i:i + number_of_threads]
                    futures.append(executor.submit(extract_traders_from_token, chunk))
                
                # Wait for all futures to complete
                for future in as_completed(futures):
                    try:
                        future.result()  # This will raise any exceptions caught in the worker function
                    except Exception as e:
                        debug_print(f"Error in processing future: {e}")
        else:
            debug_print("No trending tokens found in the database.")

    except mysql.connector.Error as err:
        debug_print(f"Database error: {err}")
        sqldb.rollback()
    
    finally:
        if sql_cursor:
            sql_cursor.close()
        if sqldb:
            sqldb.close()
    
    
    