import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from webscraper import scrape_nse_announcements_robust # Import the existing scraper

# Load symbols from SYMBOLS.csv
try:
    symbols_df = pd.read_csv('SYMBOLS.csv')
    TICKER_SYMBOLS = symbols_df['TckrSymb'].tolist()
except FileNotFoundError:
    st.error("SYMBOLS.csv not found. Please ensure it's in the same directory.")
    TICKER_SYMBOLS = ["AXISBANK"] # Fallback
except Exception as e:
    st.error(f"Error loading SYMBOLS.csv: {e}")
    TICKER_SYMBOLS = ["AXISBANK"] # Fallback

def get_announcements_for_symbol(symbol: str, start_date: datetime = None, end_date: datetime = None, limit: int = None):
    """
    Fetches corporate announcements for a given symbol and filters by date range.
    Uses the existing scrape_nse_announcements_robust function.
    """
    st.info(f"Fetching announcements for {symbol}...")
    
    # Call the existing scraper, passing the limit
    df = scrape_nse_announcements_robust(symbol, limit=limit)
    
    if df.empty:
        st.warning(f"No announcements found for {symbol}.")
        return pd.DataFrame()

    # Convert 'Broadcast Date' to datetime objects for filtering
    # Let Pandas infer the format for robustness
    try:
        df['Broadcast Date'] = pd.to_datetime(df['Broadcast Date'], errors='coerce')
        df.dropna(subset=['Broadcast Date'], inplace=True)
    except Exception as e:
        st.error(f"Error parsing 'Broadcast Date' column: {e}")
        return pd.DataFrame()

    # Filter by date range if provided
    if start_date and end_date:
        df = df[(df['Broadcast Date'] >= start_date) & (df['Broadcast Date'] <= end_date)]
        st.info(f"Filtered announcements from {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}.")
    
    # Sort by date in descending order (latest first)
    df = df.sort_values(by='Broadcast Date', ascending=False)

    # Apply limit if provided (redundant if limit was already applied in scraper, but harmless)
    if limit:
        df = df.head(limit)
        st.info(f"Displaying the latest {limit} announcements.")

    return df

def render_corporate_announcements_tab():
    st.title("NSE Corporate Announcements")
    st.write("Select a stock symbol to view corporate announcements.")

    symbol = st.selectbox("Select Stock Symbol", TICKER_SYMBOLS, index=TICKER_SYMBOLS.index("AXISBANK") if "AXISBANK" in TICKER_SYMBOLS else 0)

    fetch_latest_button = st.button("Fetch Latest 10 Reports")

    if fetch_latest_button:
        if symbol:
            with st.spinner("Fetching latest 10 reports... This may take a moment due to web scraping."):
                latest_announcements_df = get_announcements_for_symbol(symbol, limit=10)
                if not latest_announcements_df.empty:
                    st.subheader(f"Latest 10 Announcements for {symbol}")
                    
                    # Create a 'View Report' column with hyperlinks
                    # The LinkColumn will automatically display "View Report" if the value is a URL
                    latest_announcements_df['View Report'] = latest_announcements_df['Attachment Link']
                    
                    st.dataframe(latest_announcements_df[['Symbol', 'Company Name', 'Subject', 'Broadcast Date', 'View Report']],
                                 column_config={"View Report": st.column_config.LinkColumn("View Report", display_text="View Report")})

                    csv_output = latest_announcements_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Latest 10 Results as CSV",
                        data=csv_output,
                        file_name=f"{symbol}_latest_10_announcements.csv",
                        mime="text/csv",
                    )
                else:
                    st.warning("No latest announcements found for the selected symbol.")
        else:
            st.warning("Please enter a stock symbol.")