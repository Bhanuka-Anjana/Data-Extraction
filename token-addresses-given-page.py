# pip install seleniumbase beautifulsoup4 requests regex

import time
import re
from seleniumbase import SB # Import SeleniumBase
from bs4 import BeautifulSoup
import requests # For initial check
import regex # Using regex library

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
    print(f"Attempting to scrape with SeleniumBase: {url}")

    # --- Initial Check (Optional but Recommended) ---
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code != 200 and response.status_code != 403: # 403 might indicate CF challenge page
             print(f"Warning: Initial request failed with status code {response.status_code}. Proceeding with SeleniumBase.")
             # return [] # Optionally exit here
    except requests.exceptions.RequestException as e:
        print(f"Warning: Error during initial request: {e}. Proceeding with SeleniumBase.")
        # return [] # Optionally exit here

    token_addresses = set() # Use a set for automatic duplicate handling

    try:
        # Use SB context manager for automatic driver management and UC mode
        # uc=True enables undetected-chromedriver features
        # test=True can sometimes help with stability/configuration
        # locale_code sets browser language, potentially aiding bypass
        with SB(uc=True, test=True, locale_code="en", headless=True) as sb: # headless=True runs without visible browser
            print("Setting up SeleniumBase driver (uc mode)...")

            # activate_cdp_mode often used with uc=True for better interaction & navigation
            print(f"Navigating to {url} using CDP mode...")
            sb.activate_cdp_mode(url)

            # Short wait for the potential verification page to appear
            print(f"Waiting {wait_before_captcha_check}s before potential captcha click...")
            time.sleep(wait_before_captcha_check)

            # Attempt to click the Cloudflare checkbox IF it appears visually
            # SeleniumBase tries to handle this automatically, but this adds robustness
            print("Attempting uc_gui_click_captcha() (may not be needed if bypassed automatically)...")
            try:
                sb.uc_gui_click_captcha()
                print("uc_gui_click_captcha executed.")
            except Exception as captcha_click_error:
                print(f"Captcha click failed or wasn't necessary: {captcha_click_error}")

            # Wait *after* potential bypass/click for the *actual* Dexscreener content
            print(f"Waiting {wait_time_after_bypass} seconds for main page content...")
            time.sleep(wait_time_after_bypass)

            print("Getting page source after potential bypass...")
            page_source = sb.get_page_source()

            # Optional: Save source if debugging is needed
            # with open("dexscreener_sb_page.html", "w", encoding="utf-8") as f:
            #     f.write(page_source)
            # print("Page source saved to dexscreener_sb_page.html")

            print("Parsing HTML with BeautifulSoup...")
            soup = BeautifulSoup(page_source, 'html.parser')

            # --- Extraction Logic (same as before) ---
            token_icon_imgs = soup.find_all('img', class_='ds-dex-table-row-token-icon-img')

            if not token_icon_imgs:
                print("No token image elements found after bypass. Page might not have loaded correctly or structure changed.")
                # sb.save_screenshot_to_logs() # Save screenshot if needed
                return []

            print(f"Found {len(token_icon_imgs)} potential token images. Extracting addresses...")

            solana_address_pattern = regex.compile(r'/solana/([1-9A-HJ-NP-Za-km-z]{32,44})\.(?:png|jpg|jpeg|gif|webp)', regex.IGNORECASE)

            for img in token_icon_imgs:
                if img and 'src' in img.attrs:
                    src = img['src']
                    match = solana_address_pattern.search(src)
                    if match:
                        token_address = match.group(1)
                        if 32 <= len(token_address) <= 44:
                            token_addresses.add(token_address)
                        else:
                            print(f"  - Possible invalid length found: {token_address} in {src}")

            print(f"Extraction complete. Found {len(token_addresses)} unique addresses.")

    except Exception as e:
        print(f"An error occurred during SeleniumBase scraping: {e}")
        # Consider adding sb.save_screenshot_to_logs() here too on error

    # No finally block needed for sb.quit() when using 'with SB(...)' context manager

    return list(token_addresses)

# --- Main Execution ---
if __name__ == "__main__":
    target_url = "https://dexscreener.com/solana?rankBy=trendingScoreH24&order=desc"
    # Increase wait_time_after_bypass if content still doesn't load fully
    tokens = scrape_dexscreener_tokens_sb(target_url, wait_time_after_bypass=12, wait_before_captcha_check=4)

    if tokens:
        print("\n--- Found Solana Token Addresses ---")
        for i, token in enumerate(tokens):
            print(f"{i+1}. {token}")
        print(f"\nTotal unique addresses found: {len(tokens)}")
    else:
        print("\nNo token addresses were scraped. Check logs for errors or Cloudflare issues.")