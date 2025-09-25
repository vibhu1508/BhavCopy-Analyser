import streamlit as st
import pandas as pd
import zipfile
import io
import requests
import datetime as dt
import time
import altair as alt # Import Altair

# --- CONFIGURATION ---
# Base URL for the NSE F&O archives. The {date} part will be replaced automatically.
FO_BASE_URL = "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{date}_F_0000.csv.zip"

# Headers to mimic a real browser, helping to avoid connection errors.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/zip",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

# Delay between each download request in seconds to be polite to the server.
POLITE_DELAY = 1.5 # seconds

def download_and_process_fo_bhavcopy(target_date):
    """
    Downloads the NSE F&O Bhavcopy for a specific date directly into memory,
    extracts the CSV, and processes it into a DataFrame.

    Args:
        target_date (datetime.date): The date for which to download the Bhavcopy.

    Returns:
        pandas.DataFrame or None: Processed DataFrame if successful, None otherwise.
    """
    date_str = target_date.strftime("%Y%m%d")
    url = FO_BASE_URL.format(date=date_str)

    st.info(f"Attempting to download F&O data for {target_date.strftime('%d-%b-%Y')}...")

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

        required_columns = [
            'TckrSymb', 'XpryDt', 'StrkPric', 'OptnTp', 'FinInstrmNm',
            'ClsPric', 'PrvsClsgPric', 'UndrlygPric', 'SttlmPric',
            'OpnIntrst', 'ChngInOpnIntrst', 'FinInstrmTp' # Added FinInstrmTp
        ]
        
        # Check for missing columns
        missing_columns = [col for col in required_columns if col not in dataframe.columns]
        if missing_columns:
            st.error(f"Missing required columns: {', '.join(missing_columns)} for {target_date.strftime('%d-%b-%Y')}. Please ensure the BhavCopy file contains all expected columns.")
            return None
        
        # Ensure FinInstrmTp is treated as string, stripped of whitespace, and converted to uppercase for consistent filtering
        if 'FinInstrmTp' in dataframe.columns:
            dataframe['FinInstrmTp'] = dataframe['FinInstrmTp'].astype(str).str.strip().str.upper()

        dataframe = dataframe[required_columns]

        # Convert relevant columns to numeric, coercing errors
        numeric_cols = ['ClsPric', 'PrvsClsgPric', 'UndrlygPric', 'SttlmPric', 'OpnIntrst', 'ChngInOpnIntrst', 'StrkPric']
        for col in numeric_cols:
            dataframe[col] = pd.to_numeric(dataframe[col], errors='coerce')
        
        # Drop rows where essential numeric columns are NaN, excluding StrkPric for futures
        # Futures typically have NaN for StrkPric, so dropping based on it would remove them.
        dataframe.dropna(subset=['ClsPric', 'OpnIntrst', 'ChngInOpnIntrst'], inplace=True)

        # Calculate %CH IN OI
        # Handle cases where (OpnIntrst - ChngInOpnIntrst) might be zero or negative
        prev_oi = dataframe['OpnIntrst'] - dataframe['ChngInOpnIntrst']
        dataframe['%CH IN OI'] = (dataframe['ChngInOpnIntrst'] / prev_oi.replace(0, pd.NA)) * 100
        dataframe['%CH IN OI'].fillna(0, inplace=True) # Fill NaN (from division by zero) with 0
        
        st.success(f"Successfully processed F&O data for {target_date.strftime('%d-%b-%Y')}.")
        time.sleep(POLITE_DELAY) # Be polite to the server
        return dataframe

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            st.warning(f"No F&O data found for {target_date.strftime('%d-%b-%Y')}. It might be a weekend or a trading holiday.")
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

def render_options_tab(df):
    st.subheader("Options Analysis")
    if df is None or df.empty:
        st.info("No options data available or uploaded.")
        return

    options_df = df[df['FinInstrmNm'].str.contains('CE|PE', na=False)]

    if options_df.empty:
        st.info("No options data found in the uploaded file.")
        return

    # Dropdowns for filtering
    unique_symbols = options_df['TckrSymb'].unique()
    selected_symbol = st.selectbox("Select Ticker Symbol", unique_symbols, key="options_symbol_select")

    filtered_by_symbol = options_df[options_df['TckrSymb'] == selected_symbol]

    unique_expiries = filtered_by_symbol['XpryDt'].unique()
    selected_expiry = st.selectbox("Select Expiry Date", unique_expiries, key="options_expiry_select")

    final_options_df = filtered_by_symbol[filtered_by_symbol['XpryDt'] == selected_expiry]

    if final_options_df.empty:
        st.info("No data for selected symbol and expiry.")
        return

    # Prepare data for CE and PE, including OI and Change in OI
    ce_df = final_options_df[final_options_df['OptnTp'] == 'CE'][['StrkPric', 'ClsPric', '%CH IN OI', 'OpnIntrst', 'ChngInOpnIntrst']].rename(columns={
        'ClsPric': 'CE_ClsPric', 
        '%CH IN OI': 'CE_%CH IN OI',
        'OpnIntrst': 'CE_OpnIntrst',
        'ChngInOpnIntrst': 'CE_ChngInOpnIntrst'
    })
    pe_df = final_options_df[final_options_df['OptnTp'] == 'PE'][['StrkPric', 'ClsPric', '%CH IN OI', 'OpnIntrst', 'ChngInOpnIntrst']].rename(columns={
        'ClsPric': 'PE_ClsPric', 
        '%CH IN OI': 'PE_%CH IN OI',
        'OpnIntrst': 'PE_OpnIntrst',
        'ChngInOpnIntrst': 'PE_ChngInOpnIntrst'
    })

    # Merge CE and PE data on Strike Price
    merged_options_display = pd.merge(ce_df, pe_df, on='StrkPric', how='outer')
    
    # Calculate Put-Call Open Interest Ratio (PCROI) per strike price
    merged_options_display['PCROI'] = merged_options_display['PE_OpnIntrst'] / merged_options_display['CE_OpnIntrst'].replace(0, pd.NA)
    merged_options_display['PCROI'].fillna(0, inplace=True) # Fill NaN (from division by zero) with 0

    # Sort by %CH IN OI in descending order, handling potential NaN values in sorting columns
    merged_options_display['CE_%CH IN OI_sort'] = merged_options_display['CE_%CH IN OI'].fillna(-float('inf'))
    merged_options_display['PE_%CH IN OI_sort'] = merged_options_display['PE_%CH IN OI'].fillna(-float('inf'))
    
    merged_options_display = merged_options_display.sort_values(
        by=['CE_%CH IN OI_sort', 'PE_%CH IN OI_sort'], 
        ascending=[False, False]
    ).drop(columns=['CE_%CH IN OI_sort', 'PE_%CH IN OI_sort'])

    st.dataframe(merged_options_display)

    # --- Chart 1: Open Interest (CE vs PE) ---
    st.subheader("Open Interest by Strike Price")

    # Melt the DataFrame to long format for Altair
    oi_chart_data = merged_options_display[['StrkPric', 'CE_OpnIntrst', 'PE_OpnIntrst']].melt(
        id_vars=['StrkPric'], 
        var_name='Option Type', 
        value_name='Open Interest'
    )

    # Define colors
    color_scale_oi = alt.Scale(domain=['CE_OpnIntrst', 'PE_OpnIntrst'], range=['green', 'red'])

    chart_oi = alt.Chart(oi_chart_data).mark_bar().encode(
        x=alt.X('StrkPric:Q', title='Strike Price'),
        y=alt.Y('Open Interest:Q', title='Open Interest'),
        color=alt.Color('Option Type:N', scale=color_scale_oi, legend=alt.Legend(title="Option Type")),
        tooltip=['StrkPric', 'Option Type', 'Open Interest']
    ).properties(
        title=f"Open Interest for {selected_symbol} (Expiry: {selected_expiry})"
    ).interactive()
    st.altair_chart(chart_oi, use_container_width=True)

    # --- Chart 2: Change in Open Interest (CE vs PE) ---
    st.subheader("Change in Open Interest by Strike Price")

    # Melt the DataFrame to long format for Altair
    pct_oi_chart_data = merged_options_display[['StrkPric', 'CE_ChngInOpnIntrst', 'PE_ChngInOpnIntrst']].melt(
        id_vars=['StrkPric'], 
        var_name='Option Type', 
        value_name='Change in Open Interest'
    )

    # Define colors for Change in Open Interest
    color_scale_chng_oi = alt.Scale(domain=['CE_ChngInOpnIntrst', 'PE_ChngInOpnIntrst'], range=['green', 'red'])

    chart_chng_oi = alt.Chart(pct_oi_chart_data).mark_bar().encode(
        x=alt.X('StrkPric:Q', title='Strike Price'),
        y=alt.Y('Change in Open Interest:Q', title='Change in Open Interest'),
        color=alt.Color('Option Type:N', scale=color_scale_chng_oi, legend=alt.Legend(title="Option Type")),
        tooltip=['StrkPric', 'Option Type', 'Change in Open Interest']
    ).properties(
        title=f"Change in Open Interest for {selected_symbol} (Expiry: {selected_expiry})"
    ).interactive()
    st.altair_chart(chart_chng_oi, use_container_width=True)


def render_futures_tab(df):
    st.subheader("Futures Analysis")
    if df is None or df.empty:
        st.info("No futures data available or uploaded.")
        return
    
    # The user wants to filter solely by FinInstrmTp for futures (IDF and STF)
    # No need for FinInstrmNm.str.upper().str.endswith('FUT') or OptnTp.isna() here.

    index_futures_tab, stock_futures_tab = st.tabs(["Index Futures (IDF)", "Stock Futures (STF)"]) # Reverted tab titles

    with index_futures_tab:
        st.subheader("Index Futures (IDF)") # Reverted subheader
        idf_df = df[df['FinInstrmTp'] == 'IDF'] # Reverted filter to 'IDF'

        if idf_df.empty:
            st.info("No Index Futures (IDF) data found for the selected date.") # Reverted message
        else:
            unique_symbols_idf = idf_df['TckrSymb'].unique()
            selected_symbol_idf = st.selectbox("Select Ticker Symbol (IDF)", unique_symbols_idf, key="idf_symbol_select") # Reverted key and label

            filtered_by_symbol_idf = idf_df[idf_df['TckrSymb'] == selected_symbol_idf]

            # Remove Expiry Date Dropdown, filter only by Ticker Symbol
            final_idf_df = filtered_by_symbol_idf.copy() # Use .copy() to avoid SettingWithCopyWarning

            if final_idf_df.empty:
                st.info("No data for selected Index Futures symbol.")
            else:
                # Calculate Percentage Change in Closing Price
                final_idf_df['Percentage_Change_Price'] = ((final_idf_df['ClsPric'] - final_idf_df['PrvsClsgPric']) / final_idf_df['PrvsClsgPric'].replace(0, pd.NA)) * 100
                final_idf_df['Percentage_Change_Price'].fillna(0, inplace=True)

                # Select, reorder, and rename columns
                display_columns_idf = final_idf_df[[
                    'FinInstrmNm', 'UndrlygPric', 'ClsPric',  
                    'PrvsClsgPric','Percentage_Change_Price', 'OpnIntrst', 'ChngInOpnIntrst', '%CH IN OI'
                ]].rename(columns={
                    'FinInstrmNm': 'Financial Instrument Name',
                    'UndrlygPric': 'Underlying Price',
                    'ClsPric': 'Closing Price',
                    'Percentage_Change_Price': '% Change Price',
                    'PrvsClsgPric': 'Previous Closing Price',
                    'OpnIntrst': 'Open Interest',
                    'ChngInOpnIntrst': 'Change in Open Interest',
                    '%CH IN OI': '% Change in OI'
                })
                st.dataframe(display_columns_idf)

    with stock_futures_tab:
        st.subheader("Stock Futures (STF)") # Reverted subheader
        stf_df = df[df['FinInstrmTp'] == 'STF'] # Reverted filter to 'STF'

        if stf_df.empty:
            st.info("No Stock Futures (STF) data found for the selected date.") # Reverted message
        else:
            unique_symbols_stf = stf_df['TckrSymb'].unique()
            selected_symbol_stf = st.selectbox("Select Ticker Symbol (STF)", unique_symbols_stf, key="stf_symbol_select")

            # Remove Expiry Date Dropdown, filter only by Ticker Symbol
            filtered_by_symbol_stf = stf_df[stf_df['TckrSymb'] == selected_symbol_stf]
            final_stf_df = filtered_by_symbol_stf.copy() # Use .copy() to avoid SettingWithCopyWarning

            if final_stf_df.empty:
                st.info("No data for selected Stock Futures symbol.")
            else:
                # Calculate Percentage Change in Closing Price
                final_stf_df['Percentage_Change_Price'] = ((final_stf_df['ClsPric'] - final_stf_df['PrvsClsgPric']) / final_stf_df['PrvsClsgPric'].replace(0, pd.NA)) * 100
                final_stf_df['Percentage_Change_Price'].fillna(0, inplace=True)

                # Select, reorder, and rename columns
                display_columns_stf = final_stf_df[[
                    'FinInstrmNm', 'UndrlygPric', 'ClsPric', 
                    'PrvsClsgPric','Percentage_Change_Price', 'OpnIntrst', 'ChngInOpnIntrst', '%CH IN OI'
                ]].rename(columns={
                    'FinInstrmNm': 'Instrument Name',
                    'UndrlygPric': 'Underlying Price',
                    'ClsPric': 'Closing Price',
                    'PrvsClsgPric': 'Previous Closing Price',
                    'Percentage_Change_Price': '% Change Price',
                    'OpnIntrst': 'Open Interest',
                    'ChngInOpnIntrst': 'Change in Open Interest',
                    '%CH IN OI': '% Change in OI'
                })
                st.dataframe(display_columns_stf)

def render_nifty_tab(df):
    st.subheader("Nifty Analysis")
    if df is None or df.empty:
        st.info("No Nifty data available or uploaded.")
        return
    
    # Filter for Nifty options (assuming NIFTY options are also present in the data with CE/PE)
    nifty_options_df = df[df['FinInstrmNm'].str.contains('NIFTY') & df['FinInstrmNm'].str.contains('CE|PE', na=False)]

    if nifty_options_df.empty:
        st.info("No Nifty options data found in the uploaded file.")
        return

    unique_symbols = nifty_options_df['TckrSymb'].unique()
    selected_symbol = st.selectbox("Select Ticker Symbol", unique_symbols, key="nifty_symbol_select")

    filtered_by_symbol = nifty_options_df[nifty_options_df['TckrSymb'] == selected_symbol]

    unique_expiries = filtered_by_symbol['XpryDt'].unique()
    selected_expiry = st.selectbox("Select Expiry Date", unique_expiries, key="nifty_expiry_select")

    final_nifty_df = filtered_by_symbol[filtered_by_symbol['XpryDt'] == selected_expiry]

    if final_nifty_df.empty:
        st.info("No data for selected symbol and expiry.")
        return
    
    # Prepare data for CE and PE, including OI and Change in OI
    ce_df = final_nifty_df[final_nifty_df['OptnTp'] == 'CE'][['StrkPric', 'ClsPric', '%CH IN OI', 'OpnIntrst', 'ChngInOpnIntrst']].rename(columns={
        'ClsPric': 'CE_ClsPric', 
        '%CH IN OI': 'CE_%CH IN OI',
        'OpnIntrst': 'CE_OpnIntrst',
        'ChngInOpnIntrst': 'CE_ChngInOpnIntrst'
    })
    pe_df = final_nifty_df[final_nifty_df['OptnTp'] == 'PE'][['StrkPric', 'ClsPric', '%CH IN OI', 'OpnIntrst', 'ChngInOpnIntrst']].rename(columns={
        'ClsPric': 'PE_ClsPric', 
        '%CH IN OI': 'PE_%CH IN OI',
        'OpnIntrst': 'PE_OpnIntrst',
        'ChngInOpnIntrst': 'PE_ChngInOpnIntrst'
    })

    # Merge CE and PE data on Strike Price
    merged_nifty_display = pd.merge(ce_df, pe_df, on='StrkPric', how='outer')

    # Calculate Put-Call Open Interest Ratio (PCROI) per strike price
    merged_nifty_display['PCROI'] = merged_nifty_display['PE_OpnIntrst'] / merged_nifty_display['CE_OpnIntrst'].replace(0, pd.NA)
    merged_nifty_display['PCROI'].fillna(0, inplace=True) # Fill NaN (from division by zero) with 0

    # Sort by %CH IN OI in descending order, handling potential NaN values in sorting columns
    merged_nifty_display['CE_%CH IN OI_sort'] = merged_nifty_display['CE_%CH IN OI'].fillna(-float('inf'))
    merged_nifty_display['PE_%CH IN OI_sort'] = merged_nifty_display['PE_%CH IN OI'].fillna(-float('inf'))
    
    merged_nifty_display = merged_nifty_display.sort_values(
        by=['CE_%CH IN OI_sort', 'PE_%CH IN OI_sort'], 
        ascending=[False, False]
    ).drop(columns=['CE_%CH IN OI_sort', 'PE_%CH IN OI_sort'])

    st.dataframe(merged_nifty_display)


def render_new_functionality_tab():
    st.title("Advanced Market Analysis")
    st.write("Select a date to analyze Nifty, Futures, and Options data.")

    today = dt.date.today()
    selected_date = st.date_input("Select Date", value=today, key="fo_date_select")

    # Initialize session state for DataFrame if not already present
    if 'fo_data_df' not in st.session_state:
        st.session_state['fo_data_df'] = None

    if st.button("Get Analysis", key="get_analysis_fo_button"):
        if selected_date:
            st.session_state['fo_data_df'] = download_and_process_fo_bhavcopy(selected_date)
        else:
            st.warning("Please select a date to proceed.")

    nifty_tab, futures_tab, options_tab = st.tabs(["Nifty", "Futures", "Options"])

    with nifty_tab:
        render_nifty_tab(st.session_state['fo_data_df'])
    with futures_tab:
        render_futures_tab(st.session_state['fo_data_df'])
    with options_tab:
        render_options_tab(st.session_state['fo_data_df'])
        #
