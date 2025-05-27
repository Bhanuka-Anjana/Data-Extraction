# pip install seleniumbase beautifulsoup4 requests regex
from seleniumbase import SB # Import SeleniumBase
from bs4 import BeautifulSoup
import regex # Using regex library
from concurrent.futures import ProcessPoolExecutor, as_completed
import threading

DEBUG_PRINT = True  # Set to True for debugging output

def debug_print(message):
    if DEBUG_PRINT:
        thread = threading.current_thread()
        thread_info = f"[{thread.name} | ID: {thread.ident}]"
        print(f"{thread_info}  :: {message}")

def scrape_each_token_address(url, wait_time_after_bypass=10, wait_before_captcha_check=3):
    debug_print(f"Attempting to scrape with SeleniumBase: {url}")
    
    # create a list that stores dictionaries of token info
    wallet_addresses = []

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
            debug_print(f"Waiting {wait_before_captcha_check}s before potential captcha click...")
            sb.sleep(wait_before_captcha_check)

            # Attempt to click the Cloudflare checkbox IF it appears visually
            # SeleniumBase tries to handle this automatically, but this adds robustness
            debug_print("Attempting uc_gui_click_captcha() (may not be needed if bypassed automatically)...")
            try:
                sb.uc_gui_click_captcha()
                debug_print("uc_gui_click_captcha executed.")
            except Exception as captcha_click_error:
                debug_print(f"Captcha click failed or wasn't necessary: {captcha_click_error}")

          
           
            # Wait *after* potential bypass/click for the *actual* Dexscreener content
            debug_print(f"Waiting {wait_time_after_bypass} seconds for main page content...")
            # sb.sleep(wait_time_after_bypass)
            
            # wait until the class custom-1oq7u8k loads
            try:
                debug_print("Waiting for the class custom-1oq7u8k elements to load...")
                sb.wait_for_element_visible('div.custom-1oq7u8k', timeout=100)
                debug_print("Class custom-1oq7u8k elements are now visible.")
            except Exception as e:
                debug_print(f"Error waiting for class custom-1oq7u8k elements: {e}")
                # Consider adding sb.save_screenshot_to_logs() here too on error
                return []
            
            
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
                    return []
                
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
                        wallet_addresses.append(wallet_address)
                
                
            except Exception as e:
                debug_print(f"Error clicking 'Top Traders' button: {e}")

    except Exception as e:
        debug_print(f"An error occurred during SeleniumBase scraping: {e}")
        # Consider adding sb.save_screenshot_to_logs() here too on error

    return list(wallet_addresses)
    
def scrape_dexscreener_tokens_sb(url, wait_time_after_bypass=10, wait_before_captcha_check=3):
    """
    Scrapes Solana token addresses from a Dexscreener URL using SeleniumBase
    to handle Cloudflare verification.

    Args:
        url (str): The Dexscreener URL to scrape.
        wait_time_after_bypass (int): How many seconds to wait AFTER potential
                                      Cloudflare bypass for the main page content
                                      to load dynamically. Adjust if needed.
        wait_before_captcha_check (int): Short wait before checking/clicking captcha.

    Returns:
        list: A list of unique Solana token addresses found on the page.
              Returns an empty list if scraping fails or no tokens are found.
    """
    debug_print(f"Attempting to scrape with SeleniumBase: {url}")

    # create a list that stores dictionaries of token info
    token_addresses = []

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
            debug_print(f"Waiting {wait_before_captcha_check}s before potential captcha click...")
            sb.sleep(wait_before_captcha_check)

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

            if not token_icon_imgs:
                debug_print("No token image elements found after bypass. Page might not have loaded correctly or structure changed.")
                # sb.save_screenshot_to_logs() # Save screenshot if needed
                return []

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
                            
                            token_addresses.append(token_info)
                            
                        else:
                            debug_print(f"  - Possible invalid length found: {token_address} in {src}")
            debug_print(f"Extraction complete. Found {len(token_addresses)} unique addresses.")
            debug_print(f"Extraction complete. Found {len(token_addresses)} unique addresses.")

    except Exception as e:
        debug_print(f"An error occurred during SeleniumBase scraping: {e}")
        # Consider adding sb.save_screenshot_to_logs() here too on error

    return list(token_addresses)

# --- Main Execution ---
if __name__ == "__main__":
    target_url = "https://dexscreener.com/solana?rankBy=trendingScoreH24&order=desc"
    # Increase wait_time_after_bypass if content still doesn't load fully
    tokens = scrape_dexscreener_tokens_sb(target_url, wait_time_after_bypass=12, wait_before_captcha_check=4)

    # if tokens:
    #     debug_print("\n--- Found Solana Token Addresses ---")
    #     for i, token in enumerate(tokens):
    #         debug_print(f"{i+1}. Address: {token['address']}, Name: {token['name']}, Market Cap: {token['market_cap']}, Liquidity: {token['liquidity']}, Volume: {token['volume']}")
    #     debug_print(f"\nTotal unique addresses found: {len(tokens)}")
    # else:
    #     debug_print("\nNo token addresses were scraped. Check logs for errors or Cloudflare issues.")
    
    # debug_print the number of tokens found
    debug_print(f"Number of tokens found: {len(tokens)}")
    
    # get  the traders with their wallet addresses who traded the of the first token
    # if tokens:
    #     # first_token = tokens[0]
    #     # debug_print(f"First token address: {first_token['address']}")
    #     # traders = scrape_each_token_address(first_token['link'], wait_time_after_bypass=12, wait_before_captcha_check=4)
    #     # debug_print(f"Number of traders found: {len(traders)}")
        
    if tokens:
        debug_print(f"\n--- Starting parallel scraping for {len(tokens)} tokens ---")
        
        # Limit the number of concurrent processes based on your system capacity
        max_workers = 2  # Adjust based on your CPU/RAM
        results = {}

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_token = {
                executor.submit(scrape_each_token_address, token['link']): token['name']
                for token in tokens
            }

            # Process results as they complete
            for future in as_completed(future_to_token):
                token_name = future_to_token[future]
                try:
                    wallet_addresses = future.result()
                    results[token_name] = wallet_addresses
                    debug_print(f"{token_name}: {len(wallet_addresses)} trader addresses found.")
                except Exception as exc:
                    debug_print(f"{token_name} generated an exception: {exc}")

        # Optional: debug_print all results
        debug_print("\n--- All Results ---")
        for name, addresses in results.items():
            debug_print(f"{name} ({len(addresses)} traders): {addresses}")
        
        
    else:
        debug_print("No tokens found to scrape traders from.")