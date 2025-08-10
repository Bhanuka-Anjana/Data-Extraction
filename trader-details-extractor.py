from seleniumbase import SB # Import SeleniumBase
from bs4 import BeautifulSoup
import regex # type: ignore # Using regex library
from concurrent.futures import ProcessPoolExecutor, as_completed
import threading
import mysql.connector  

target_url = "https://dexcheck.ai/app/wallet-analyzer/GLGVuGemYPYg2Fy856WVUTHaghHjH42331iXqruxVYJf"

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


# --- Main Execution ---
if __name__ == "__main__":
    
    debug_print(f"Attempting to scrape with SeleniumBase: {target_url}")

    try:
        with SB(uc=True, test=True, locale_code="en", headless=False) as sb: # headless=True runs without visible browser
            debug_print("Setting up SeleniumBase driver (uc mode)...")

            # activate_cdp_mode often used with uc=True for better interaction & navigation
            debug_print(f"Navigating to {target_url} using CDP mode...")
            sb.activate_cdp_mode(target_url)

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

    except Exception as e:
        debug_print(f"An error occurred during SeleniumBase scraping: {e}")
        # Consider adding sb.save_screenshot_to_logs() here too on error
        