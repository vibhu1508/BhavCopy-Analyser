import pandas as pd
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_nse_announcements_robust(symbol="AXISBANK", limit=None):
    """
    Robust scraper for NSE corporate announcements using requests.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
    }

    # The URL for corporate announcements API with index and symbol parameter.
    url = f"https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={symbol}"

    try:
        with requests.Session() as s:
            s.headers.update(headers)

            # First, make a GET request to the main page to establish a session and get cookies.
            logger.info("Establishing session with NSE...")
            s.get("https://www.nseindia.com/companies-listing/corporate-filings-announcements")

            # Then, fetch the JSON data from the API endpoint.
            logger.info(f"Fetching data from {url}...")
            response = s.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()

            if not data:
                logger.warning("No data received from the API.")
                return pd.DataFrame()

            df = pd.DataFrame(data)

            if df.empty:
                logger.warning("DataFrame is empty after initial load.")
                return pd.DataFrame()

            # The symbol is now part of the URL, so direct filtering on the DataFrame might be redundant
            # but we keep it for robustness in case the API returns more than just the requested symbol.
            if symbol and 'symbol' in df.columns:
                df_filtered = df[df['symbol'] == symbol.upper()]
                if df_filtered.empty:
                    logger.warning(f"No announcements found for symbol: {symbol} in the 'symbol' column from the API response.")
                else:
                    logger.info(f"Filtered {len(df_filtered)} announcements for symbol: {symbol}")
                df = df_filtered
            elif symbol and 'symbol' not in df.columns:
                logger.warning("The 'symbol' column does not exist in the DataFrame. Cannot filter by symbol.")

            if limit and not df.empty:
                df = df.head(limit)
                logger.info(f"Limited to {len(df)} announcements.")

            # Rename columns to match what corporate_announcements_tab.py expects
            df = df.rename(columns={
                'symbol': 'Symbol',
                'sm_name': 'Company Name',
                'desc': 'Subject',
                'attchmntFile': 'Attachment Link',
                'an_dt': 'Broadcast Date'
            })

            # Select and reorder columns to match the expected output in corporate_announcements_tab.py
            expected_columns = ['Symbol', 'Company Name', 'Subject', 'Details', 'Attachment Link', 'Broadcast Date']
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = '' # Add missing columns with empty string defaults
            df = df[expected_columns]

            if not df.empty:
                logger.info(f"✅ Successfully scraped {len(df)} announcements")
            else:
                logger.warning("❌ No announcements extracted")

            return df

    except requests.exceptions.RequestException as e:
        logger.error(f"Error during scraping: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    symbol = "AXISBANK" # Reverted symbol to default
    
    print("=" * 60)
    print("NSE Corporate Announcements Scraper")
    print("=" * 60)
    
    # Try automated scraping
    print("\n📊 Attempting automated scraping...")
    df = scrape_nse_announcements_robust(symbol)
    
    if not df.empty:
        print(f"\n✅ Success! Scraped {len(df)} announcements")
        print("\nSample data:")
        # Using 'Subject' and 'Broadcast Date' as per renamed columns
        print(df[['Subject', 'Broadcast Date']].head(5)) 
    else:
        print(f"\n❌ Automated scraping failed for symbol: {symbol}")
        print("This might be due to no recent announcements for the symbol in the API feed.")