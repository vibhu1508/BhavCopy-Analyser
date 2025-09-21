from selenium import webdriver # type: ignore
from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore
from selenium.webdriver.chrome.options import Options # type: ignore
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException # type: ignore
from selenium.webdriver.chrome.service import Service # Import Service
from webdriver_manager.chrome import ChromeDriverManager # Import ChromeDriverManager
import pandas as pd
import time
import logging
import json
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_table_data(driver, timeout=30):
    """
    Wait for the table to be populated with actual data (not just loading row)
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Check if table has meaningful data
            rows = driver.find_elements(By.CSS_SELECTOR, "#table-CFanncEquity tbody tr")
            
            # Check if we have more than 1 row and if the first row has actual data
            if len(rows) > 1:
                first_row_text = rows[0].text
                # Check if it's not a loading message
                if first_row_text and "loading" not in first_row_text.lower() and "no data" not in first_row_text.lower():
                    logger.info(f"Table loaded with {len(rows)} data rows")
                    return True
            
            # Also check for "no records" message
            no_data_elements = driver.find_elements(By.XPATH, "//td[contains(text(), 'No records found')]")
            if no_data_elements:
                logger.warning("No records found in table")
                return False
                
        except StaleElementReferenceException:
            # Elements refreshed, which is expected during loading
            pass
        except Exception as e:
            logger.debug(f"Waiting for table: {e}")
        
        time.sleep(1)
    
    logger.warning(f"Timeout waiting for table data after {timeout} seconds")
    return False

def scrape_nse_announcements_robust(symbol="AXISBANK", limit=None):
    """
    Robust scraper for NSE corporate announcements
    """
    
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Run Chrome in headless mode
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        # Step 1: Visit main page to establish session
        logger.info("Establishing session with NSE...")
        driver.get("https://www.nseindia.com/")
        time.sleep(1) # Reduced sleep
        
        # Step 2: Navigate to announcements page
        url = f"https://www.nseindia.com/companies-listing/corporate-filings-announcements?symbol={symbol}&tabIndex=equity"
        logger.info(f"Navigating to announcements page...")
        driver.get(url)
        
        # Step 3: Wait for page to fully load
        time.sleep(2) # Reduced sleep
        
        # Step 4: Check if we need to interact with any elements
        try:
            # Sometimes there's a dropdown or button to load data
            symbol_input = driver.find_element(By.ID, "symbolCode")
            if symbol_input:
                symbol_input.clear()
                symbol_input.send_keys(symbol)
                time.sleep(0.5) # Reduced sleep
                
                # Look for a search/submit button
                search_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Search') or contains(@class, 'search')]")
                if search_buttons:
                    search_buttons[0].click()
                    time.sleep(1) # Reduced sleep
        except:
            logger.info("No search interaction needed")
        
        # Step 5: Wait for table data to load
        if not wait_for_table_data(driver, timeout=10): # Reduced timeout
            logger.warning("Table data did not load properly")
            
            # Try to trigger data load by scrolling
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5) # Reduced sleep
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5) # Reduced sleep
            
            # Check again
            wait_for_table_data(driver, timeout=5) # Reduced timeout
        
        # Step 6: Extract data with retry logic
        announcements = []
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                rows = driver.find_elements(By.CSS_SELECTOR, "#table-CFanncEquity tbody tr")
                logger.info(f"Attempting to extract from {len(rows)} rows (attempt {retry + 1})")
                
                for i, row in enumerate(rows):
                    try:
                        # Re-find elements to avoid stale references
                        current_rows = driver.find_elements(By.CSS_SELECTOR, "#table-CFanncEquity tbody tr")
                        if i >= len(current_rows):
                            break
                            
                        current_row = current_rows[i]
                        cells = current_row.find_elements(By.TAG_NAME, "td")
                        
                        if len(cells) >= 7:
                            row_text = current_row.text
                            
                            # Skip if it's a loading or no data row
                            if "no record" in row_text.lower() or "loading" in row_text.lower():
                                continue
                            
                            announcement = {
                                'Symbol': cells[0].text.strip(),
                                'Company Name': cells[1].text.strip(),
                                'Subject': cells[2].text.strip(),
                                'Details': cells[3].text.strip(),
                                'Attachment Link': '', # Changed from PDF Link
                                'Broadcast Date': ''
                            }
                            
                            # Get Attachment link (assuming it's in cells[4])
                            try:
                                attachment_link_element = cells[4].find_element(By.TAG_NAME, "a")
                                announcement['Attachment Link'] = attachment_link_element.get_attribute("href")
                            except:
                                pass
                            
                            # Get date
                            if len(cells) > 6:
                                announcement['Broadcast Date'] = cells[6].text.strip()
                            
                            # Only add if we have meaningful data
                            if announcement['Subject'] and announcement['Subject'] != '-':
                                announcements.append(announcement)
                                logger.info(f"Extracted: {announcement['Subject'][:30]}...")
                                if limit and len(announcements) >= limit:
                                    logger.info(f"Reached desired limit of {limit} announcements, stopping extraction.")
                                    break # Break out of the inner loop
                                
                    except StaleElementReferenceException:
                        logger.debug(f"Stale element at row {i}, skipping...")
                        continue
                    except Exception as e:
                        logger.debug(f"Error processing row {i}: {e}")
                        continue
                
                if announcements and (limit is None or len(announcements) >= limit):
                    break  # Success, exit retry loop
                    
            except Exception as e:
                logger.warning(f"Retry {retry + 1} failed: {e}")
                time.sleep(1) # Reduced sleep
        
        # Create DataFrame
        df = pd.DataFrame(announcements)
        
        if not df.empty:
            logger.info(f"✅ Successfully scraped {len(df)} announcements")
        else:
            logger.warning("❌ No announcements extracted")
            
            # Debug: Print page source snippet
            try:
                table_html = driver.find_element(By.ID, "table-CFanncEquity").get_attribute('innerHTML')
                logger.debug(f"Table HTML snippet: {table_html[:500]}")
            except Exception as e:
                logger.debug(f"Could not get table HTML snippet: {e}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        return pd.DataFrame()
        
    finally:
        driver.quit()

def find_api_manually():
    """
    Instructions for manually finding the API endpoint
    """
    print("""
    ====== MANUAL API DISCOVERY GUIDE ======
    
    Since automated scraping is challenging, here's how to find the API:
    
    1. Open Chrome (regular browser, not Selenium)
    
    2. Navigate to:
       https://www.nseindia.com/companies-listing/corporate-filings-announcements
    
    3. Press F12 to open DevTools
    
    4. Go to the "Network" tab
    
    5. Click on "XHR" or "Fetch" filter
    
    6. Now enter "AXISBANK" in the symbol field on the webpage
    
    7. Look in the Network tab for requests. You'll likely see something like:
       - corporate-announcements
       - getcorporateannouncements  
       - announcements-data
    
    8. Click on that request and go to "Response" tab
    
    9. If you see JSON data with announcements, that's your API!
    
    10. Right-click the request → Copy → Copy as cURL
    
    11. The URL from that cURL command is what you need
    
    Common NSE API patterns:
    - /api/corporates-pit
    - /api/corporate-actions
    - /api/merged-daily-reports
    - /api/announcements/corporates
    
    Once you find it, you can use it directly with requests library!
    """)

def use_discovered_api(api_url, symbol="AXISBANK"):
    """
    Once you discover the API, use this function
    """
    session = requests.Session()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': f'https://www.nseindia.com/companies-listing/corporate-filings-announcements?symbol={symbol}',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    # Get main page first for cookies
    session.get("https://www.nseindia.com/", headers=headers)
    
    # Now get the API
    response = session.get(api_url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data)
        print(f"✅ Successfully fetched {len(df)} records from API")
        return df
    else:
        print(f"❌ API returned status {response.status_code}")
        return None

if __name__ == "__main__":
    symbol = "AXISBANK"
    
    print("=" * 60)
    print("NSE Corporate Announcements Scraper")
    print("=" * 60)
    
    # Try automated scraping
    print("\n📊 Attempting automated scraping...")
    df = scrape_nse_announcements_robust(symbol)
    
    if not df.empty:
        print(f"\n✅ Success! Scraped {len(df)} announcements")
        print("\nSample data:")
        print(df[['Subject', 'Broadcast Date']].head(3))
    else:
        print("\n❌ Automated scraping failed")
        print("\n" + "=" * 60)
        print("RECOMMENDED: Find the API endpoint manually")
        print("=" * 60)
        find_api_manually()
        
        print("\n" + "=" * 60)
        print("Example: Once you find the API URL, use it like this:")
        print("=" * 60)
        print("""
# Example usage with discovered API:
api_url = "https://www.nseindia.com/api/[YOUR-DISCOVERED-ENDPOINT]"
df = use_discovered_api(api_url, "AXISBANK")
""")
