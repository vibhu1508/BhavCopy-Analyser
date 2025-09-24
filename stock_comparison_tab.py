import streamlit as st
import pandas as pd
import zipfile
import io
import requests
import datetime as dt
import os
import time

# --- CONFIGURATION (Copied from bhavcopy_scraper.py) ---
BASE_URL = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{date}_F_0000.csv.zip"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/zip",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}
POLITE_DELAY = 1.5 # seconds

def download_and_process_bhavcopy(target_date):
    """
    Downloads the NSE Bhavcopy for a specific date directly into memory,
    extracts the CSV, and processes it into a DataFrame.

    Args:
        target_date (datetime.date): The date for which to download the Bhavcopy.

    Returns:
        pandas.DataFrame or None: Processed DataFrame if successful, None otherwise.
    """
    date_str = target_date.strftime("%Y%m%d")
    url = BASE_URL.format(date=date_str)

    st.info(f"Attempting to download data for {target_date.strftime('%d-%b-%Y')}...")

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status() # Raise an exception for bad status codes

        # Read ZIP content from memory
        with zipfile.ZipFile(io.BytesIO(response.content), 'r') as z:
            csv_file_name = next((name for name in z.namelist() if name.endswith('.csv')), None)
            
            if csv_file_name is None:
                st.error(f"No CSV file found inside the ZIP for {target_date.strftime('%d-%b-%Y')}.")
                return None

            with z.open(csv_file_name) as csv_file:
                dataframe = pd.read_csv(io.TextIOWrapper(csv_file, 'utf-8'))

        # Required columns
        required_columns = ['TradDt', 'SctySrs', 'FinInstrmNm', 'ClsPric', 'TckrSymb', 'TtlTradgVol']
        for col in required_columns:
            if col not in dataframe.columns:
                st.error(f"Missing required column: {col} in {csv_file_name} for {target_date.strftime('%d-%b-%Y')}. Please ensure the BhavCopy file contains all expected columns.")
                return None

        dataframe = dataframe[required_columns]
        dataframe = dataframe[dataframe['SctySrs'].isin(['EQ', 'BE'])]
        dataframe['ClsPric'] = pd.to_numeric(dataframe['ClsPric'], errors='coerce')
        dataframe['TtlTradgVol'] = pd.to_numeric(dataframe['TtlTradgVol'], errors='coerce') # Convert TtlTradgVol to numeric
        dataframe.dropna(subset=['ClsPric', 'TtlTradgVol'], inplace=True) # Drop if either is missing
        
        st.success(f"Successfully processed data for {target_date.strftime('%d-%b-%Y')}.")
        time.sleep(POLITE_DELAY) # Be polite to the server
        return dataframe

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            st.warning(f"No data found for {target_date.strftime('%d-%b-%Y')}. It might be a weekend or a trading holiday.")
        else:
            st.error(f"HTTP Error for {target_date.strftime('%d-%b-%Y')}: {http_err} (Status code: {response.status_code})")
    except requests.exceptions.RequestException as req_err:
        st.error(f"A network error occurred for {target_date.strftime('%d-%b-%Y')}: {req_err}")
    except zipfile.BadZipFile:
        st.error(f"Invalid ZIP file downloaded for {target_date.strftime('%d-%b-%Y')}.")
    except Exception as e:
        st.error(f"An unexpected error occurred for {target_date.strftime('%d-%b-%Y')}: {e}")
    
    time.sleep(POLITE_DELAY) # Still wait even if there's an error
    return None

def calculate_percentage_difference(df1, df2):
    """
    Calculates the percentage difference in 'ClsPric' between two DataFrames.
    """
    if df1 is None or df2 is None:
        return None

    merged_df = pd.merge(df1, df2, on=['TckrSymb', 'FinInstrmNm'], suffixes=('_file1', '_file2'))


    merged_df['ClsPric_file1'] = merged_df['ClsPric_file1'].replace(0, pd.NA)
    merged_df['Percentage_Change_Price'] = ((merged_df['ClsPric_file2'] - merged_df['ClsPric_file1']) / merged_df['ClsPric_file1']) * 100
    
    merged_df['TtlTradgVol_file1'] = merged_df['TtlTradgVol_file1'].replace(0, pd.NA) # Handle division by zero for volume
    merged_df['Percentage_Change_Volume'] = ((merged_df['TtlTradgVol_file2'] - merged_df['TtlTradgVol_file1']) / merged_df['TtlTradgVol_file1']) * 100

    merged_df.dropna(subset=['Percentage_Change_Price', 'Percentage_Change_Volume'], inplace=True)

    result_df = merged_df[[
        'FinInstrmNm', 
        'ClsPric_file2', 
        'TtlTradgVol_file2', 
        'Percentage_Change_Volume',
        'Percentage_Change_Price'
    ]].sort_values(by='Percentage_Change_Price', ascending=False)

    result_df.rename(columns={
        'FinInstrmNm': 'Financial Instrument Name',
        'ClsPric_file2': 'Closing Price',
        'TtlTradgVol_file2': 'Total Trading Volume',
        'Percentage_Change_Volume': 'Percentage Change in Trading Volume',
        'Percentage_Change_Price': 'Percentage Change Price'
    }, inplace=True)

    return result_df

def render_stock_comparison_tab():
    st.title("NSE Stock Price Comparison Tool")
    st.write("Select two dates to compare stock prices and find percentage differences.")

    st.subheader("Select Dates for Comparison")
    
    today = dt.date.today()
    default_date1 = today - dt.timedelta(days=7) # Default to 7 days ago
    default_date2 = today # Default to today

    date1 = st.date_input("Select Start Date", value=default_date1, key="date1")
    date2 = st.date_input("Select End Date", value=default_date2, key="date2")

    if st.button("Get Analysis"):
        if date1 and date2:
            if date1 >= date2:
                st.error("The first date must be earlier than the second date.")
            else:
                st.info(f"Initiating analysis for {date1.strftime('%d-%b-%Y')} and {date2.strftime('%d-%b-%Y')}...")
                
                df1 = download_and_process_bhavcopy(date1)
                df2 = download_and_process_bhavcopy(date2)

                if df1 is not None and df2 is not None:
                    result_df = calculate_percentage_difference(df1, df2)

                    if result_df is not None and not result_df.empty:
                        st.subheader("Percentage Change in Closing Price (Descending Order)")
                        st.dataframe(result_df)

                        csv_output = result_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download Results as CSV",
                            data=csv_output,
                            file_name="percentage_change_report.csv",
                            mime="text/csv",
                        )
                    elif result_df is not None and result_df.empty:
                        st.warning("No matching stocks found after filtering and merging, or no valid price changes to display.")
                    else:
                        st.error("An error occurred during percentage difference calculation.")
                else:
                    st.error("Failed to retrieve and process data for one or both selected dates. Please check the dates and try again.")
        else:
            st.warning("Please select both dates to proceed.")

    st.markdown("---")
    st.markdown("NSE Stock Analysis")
