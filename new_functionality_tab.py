import streamlit as st
import pandas as pd
import zipfile
import io

def process_bhavcopy_zip(uploaded_zip_file):
    if uploaded_zip_file is not None:
        with zipfile.ZipFile(uploaded_zip_file, 'r') as z:
            # Assuming there's only one CSV file in the zip
            csv_file_name = [name for name in z.namelist() if name.endswith('.csv')][0]
            with z.open(csv_file_name) as csv_file:
                dataframe = pd.read_csv(io.TextIOWrapper(csv_file, 'utf-8'))
        

        required_columns = [
            'TckrSymb', 'XpryDt', 'StrkPric', 'OptnTp', 'FinInstrmNm',
            'ClsPric', 'PrvsClsgPric', 'UndrlygPric', 'SttlmPric',
            'OpnIntrst', 'ChngInOpnIntrst'
        ]
        
        # Check for missing columns
        missing_columns = [col for col in required_columns if col not in dataframe.columns]
        if missing_columns:
            st.error(f"Missing required columns: {', '.join(missing_columns)}")
            return None

        dataframe = dataframe[required_columns]

        # Convert relevant columns to numeric, coercing errors
        numeric_cols = ['ClsPric', 'PrvsClsgPric', 'UndrlygPric', 'SttlmPric', 'OpnIntrst', 'ChngInOpnIntrst', 'StrkPric']
        for col in numeric_cols:
            dataframe[col] = pd.to_numeric(dataframe[col], errors='coerce')
        
        # Drop rows where essential numeric columns are NaN
        dataframe.dropna(subset=['ClsPric', 'OpnIntrst', 'ChngInOpnIntrst', 'StrkPric'], inplace=True)

        # Calculate %CH IN OI
        # Handle cases where (OpnIntrst - ChngInOpnIntrst) might be zero or negative
        prev_oi = dataframe['OpnIntrst'] - dataframe['ChngInOpnIntrst']
        dataframe['%CH IN OI'] = (dataframe['ChngInOpnIntrst'] / prev_oi.replace(0, pd.NA)) * 100
        dataframe['%CH IN OI'].fillna(0, inplace=True) # Fill NaN (from division by zero) with 0

        return dataframe
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
    
    # Sort by %CH IN OI in descending order, handling potential NaN values in sorting columns
    merged_options_display['CE_%CH IN OI_sort'] = merged_options_display['CE_%CH IN OI'].fillna(-float('inf'))
    merged_options_display['PE_%CH IN OI_sort'] = merged_options_display['PE_%CH IN OI'].fillna(-float('inf'))
    
    merged_options_display = merged_options_display.sort_values(
        by=['CE_%CH IN OI_sort', 'PE_%CH IN OI_sort'], 
        ascending=[False, False]
    ).drop(columns=['CE_%CH IN OI_sort', 'PE_%CH IN OI_sort'])

    st.dataframe(merged_options_display)


def render_futures_tab(df):
    st.subheader("Futures Analysis")
    if df is None or df.empty:
        st.info("No futures data available or uploaded.")
        return
    
    futures_df = df[df['FinInstrmNm'].str.contains('FUT', na=False)]
    if futures_df.empty:
        st.info("No futures data found in the uploaded file.")
        return
    
    # Dropdowns for filtering
    unique_symbols = futures_df['TckrSymb'].unique()
    if not unique_symbols.size:
        st.info("No unique ticker symbols found for futures.")
        return
    selected_symbol = st.selectbox("Select Ticker Symbol", unique_symbols, key="futures_symbol_select")

    filtered_by_symbol = futures_df[futures_df['TckrSymb'] == selected_symbol]

    unique_expiries = filtered_by_symbol['XpryDt'].unique()
    selected_expiry = st.selectbox("Select Expiry Date", unique_expiries, key="futures_expiry_select")

    final_futures_df = filtered_by_symbol[filtered_by_symbol['XpryDt'] == selected_expiry]

    if final_futures_df.empty:
        st.info("No data for selected symbol and expiry.")
        return

    st.dataframe(final_futures_df)


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

    # Dropdowns for filtering
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
    st.write("Upload a BhavCopy ZIP file to analyze Nifty, Futures, and Options data.")

    uploaded_zip_file = st.file_uploader("Upload BhavCopy ZIP File", type=["zip"])

    df = None
    if uploaded_zip_file:
        df = process_bhavcopy_zip(uploaded_zip_file)

    nifty_tab, futures_tab, options_tab = st.tabs(["Nifty", "Futures", "Options"])

    with nifty_tab:
        render_nifty_tab(df)
    with futures_tab:
        render_futures_tab(df)
    with options_tab:
        render_options_tab(df)
