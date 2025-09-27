import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from webscraper import scrape_nse_announcements_robust # Import the existing NSE scraper
from bse_announcements_tab import render_bse_announcements_tab # Import the new BSE announcements tab

# Load symbols from SYMBOLS.csv for NSE
try:
    symbols_df = pd.read_csv('SYMBOLS.csv')
    NSE_TICKER_SYMBOLS = ["ALL COMPANIES"] + symbols_df['TckrSymb'].tolist() # Add "ALL COMPANIES" option
except FileNotFoundError:
    st.error("SYMBOLS.csv not found. Please ensure it's in the same directory.")
    NSE_TICKER_SYMBOLS = ["ALL COMPANIES", "AXISBANK"] # Fallback
except Exception as e:
    st.error(f"Error loading SYMBOLS.csv: {e}")
    NSE_TICKER_SYMBOLS = ["ALL COMPANIES", "AXISBANK"] # Fallback

def get_nse_announcements_for_symbol(symbol: str = None, start_date: datetime = None, end_date: datetime = None, limit: int = None):
    """
    Fetches corporate announcements for a given NSE symbol (or all companies if symbol is None)
    and filters by date range. Uses the existing scrape_nse_announcements_robust function.
    """
    if symbol:
        st.info(f"Fetching NSE announcements for {symbol}...")
    else:
        st.info("Fetching NSE announcements for all companies...")
    
    # Format dates for the scraper if provided
    from_date_str = start_date.strftime('%d-%m-%Y') if start_date else None
    to_date_str = end_date.strftime('%d-%m-%Y') if end_date else None

    df = scrape_nse_announcements_robust(symbol, from_date=from_date_str, to_date=to_date_str, limit=limit)
    
    if df.empty:
        st.warning(f"No NSE announcements found for {symbol if symbol else 'all companies'}.")
        return pd.DataFrame()

    try:
        df['Broadcast Date'] = pd.to_datetime(df['Broadcast Date'], errors='coerce')
        df.dropna(subset=['Broadcast Date'], inplace=True)
    except Exception as e:
        st.error(f"Error parsing 'Broadcast Date' column for NSE: {e}")
        return pd.DataFrame()
    
    df = df.sort_values(by='Broadcast Date', ascending=False)

    if limit:
        df = df.head(limit)
        st.info(f"Displaying the latest {limit} NSE announcements.")

    return df

def render_corporate_announcements_tab():
    st.title("Corporate Announcements")
    
    tab_nse, tab_bse = st.tabs(["NSE Corporate Announcements", "BSE Corporate Announcements"])

    with tab_nse:
        st.header("NSE Corporate Announcements")
        
        # Layout for a single portion
        col1, col2 = st.columns([2, 1]) # Adjust column width for better aesthetics

        with col1:
            st.subheader("Filter by Date Range")
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7), key="nse_start_date")
            end_date = st.date_input("End Date", datetime.now(), key="nse_end_date")

            symbol_selected = st.selectbox(
                "Select Company (Optional)", # Changed label to match BSE tab
                NSE_TICKER_SYMBOLS, 
                index=0, # Default to "ALL COMPANIES"
                key="nse_company_select" # Added unique key
            )
            
            # Convert "ALL COMPANIES" to None for the scraper
            symbol_for_scraper = None if symbol_selected == "ALL COMPANIES" else symbol_selected

            fetch_button_label = "Fetch NSE Reports"
            fetch_button = st.button(fetch_button_label, key="nse_fetch_button")

        with col2:
            st.empty() # Placeholder for potential future elements or just for spacing

        if fetch_button:
            if symbol_selected:
                with st.spinner(f"Fetching NSE reports for {symbol_selected} from {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}... This may take a moment due to web scraping."):
                    announcements_df = get_nse_announcements_for_symbol(symbol_for_scraper, start_date=start_date, end_date=end_date)
                    if not announcements_df.empty:
                        st.subheader(f"Announcements for {symbol_selected} from {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}")
                        
                        announcements_df['View Report'] = announcements_df['Attachment Link']
                        
                        st.dataframe(announcements_df[['Symbol', 'Company Name', 'Subject', 'Broadcast Date', 'View Report']],
                                     column_config={"View Report": st.column_config.LinkColumn("View Report", display_text="View Report")})

                        csv_output = announcements_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download NSE Results as CSV",
                            data=csv_output,
                            file_name=f"{symbol_selected}_nse_announcements_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                        )
                    else:
                        st.warning(f"No NSE announcements found for {symbol_selected} in the selected date range.")
            else:
                st.warning("Please select an NSE stock symbol or 'ALL COMPANIES'.")

    with tab_bse:
        render_bse_announcements_tab()