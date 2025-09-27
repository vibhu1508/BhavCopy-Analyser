import pandas as pd
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_nse_announcements_robust(symbol: str = None, from_date: str = None, to_date: str = None, limit=None):
    """
    Robust scraper for NSE corporate announcements using requests, with optional date range.
    from_date and to_date should be in 'DD-MM-YYYY' format.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
    }

    # Base URL for corporate announcements API
    url = "https://www.nseindia.com/api/corporate-announcements?index=equities"

    # Add symbol parameter only if provided
    if symbol:
        url += f"&symbol={symbol}"
    
    # Add date range parameters if provided
    if from_date:
        url += f"&from_date={from_date}"
    if to_date:
        url += f"&to_date={to_date}"
    
    # Add reqXbrl parameter as per user's example
    url += "&reqXbrl=false"

    try:
        with requests.Session() as s:
            s.headers.update(headers)

            # It seems the NSE API requires a session to be established first,
            # even if the user wants to directly use the API.
            # The previous attempt to remove session establishment caused a 401 error locally.
            # Re-adding the session establishment call.
            logger.info("Establishing session with NSE...")
            session_response = s.get("https://www.nseindia.com/companies-listing/corporate-filings-announcements")
            session_response.raise_for_status() # Ensure session establishment was successful
            logger.info(f"Session established with status: {session_response.status_code}")

            # Then, fetch the JSON data from the API endpoint.
            logger.info(f"Fetching data from {url}...")
            # Add Referer header for the API call, as it's often checked by websites
            s.headers.update({"Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements"})
            response = s.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError as e:
                logger.error(f"JSON decoding error: {e}. Raw response: {response.text[:500]}...") # Log first 500 chars of raw response
                return pd.DataFrame()

            if not data:
                logger.warning("No data received from the API.")
                return pd.DataFrame()

            df = pd.DataFrame(data)

            if df.empty:
                logger.warning("DataFrame is empty after initial load.")
                return pd.DataFrame()

            # If a symbol was provided, filter the DataFrame by symbol.
            # This is a safeguard in case the API returns data for multiple symbols even with the symbol parameter.
            if symbol and 'symbol' in df.columns:
                df_filtered = df[df['symbol'] == symbol.upper()]
                if df_filtered.empty:
                    logger.warning(f"No announcements found for symbol: {symbol} in the 'symbol' column from the API response.")
                else:
                    logger.info(f"Filtered {len(df_filtered)} announcements for symbol: {symbol}")
                df = df_filtered
            elif symbol and 'symbol' not in df.columns:
                logger.warning("The 'symbol' column does not exist in the DataFrame. Cannot filter by symbol.")
            elif not symbol: # If no symbol was provided, we expect all companies, so no symbol filtering needed here.
                logger.info("Fetching announcements for all companies. No symbol-specific filtering applied post-API call.")

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
        if 'response' in locals() and response is not None:
            logger.error(f"Raw response on RequestException: {response.text[:500]}...")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        if 'response' in locals() and response is not None:
            logger.error(f"Raw response on unexpected error: {response.text[:500]}...")
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
