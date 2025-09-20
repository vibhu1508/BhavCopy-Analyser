import streamlit as st
import pandas as pd
from io import StringIO

def process_csv(file_upload):
    """
    Processes a single CSV file: reads, selects columns, filters rows, and converts 'ClsPric' to numeric.
    """
    if file_upload is not None:
        dataframe = pd.read_csv(file_upload)

        required_columns = ['TradDt', 'SctySrs', 'FinInstrmNm', 'ClsPric', 'TckrSymb']
        for col in required_columns:
            if col not in dataframe.columns:
                st.error(f"Missing required column: {col} in {file_upload.name}")
                return None
        
        dataframe = dataframe[required_columns]

        dataframe = dataframe[dataframe['SctySrs'].isin(['EQ', 'BE'])]

        dataframe['ClsPric'] = pd.to_numeric(dataframe['ClsPric'], errors='coerce')
        
        dataframe.dropna(subset=['ClsPric'], inplace=True)

        return dataframe
    return None

def calculate_percentage_difference(df1, df2):
    """
    Calculates the percentage difference in 'ClsPric' between two DataFrames.
    """
    if df1 is None or df2 is None:
        return None

    merged_df = pd.merge(df1, df2, on=['TckrSymb', 'FinInstrmNm'], suffixes=('_file1', '_file2'))


    merged_df['ClsPric_file1'] = merged_df['ClsPric_file1'].replace(0, pd.NA)
    merged_df['Percentage_Change'] = ((merged_df['ClsPric_file2'] - merged_df['ClsPric_file1']) / merged_df['ClsPric_file1']) * 100

    merged_df.dropna(subset=['Percentage_Change'], inplace=True)

    result_df = merged_df[['FinInstrmNm', 'Percentage_Change']].sort_values(by='Percentage_Change', ascending=False)

    return result_df

def render_stock_comparison_tab():
    st.title("NSE Stock Price Comparison Tool")
    st.write("Upload two BhavCopy CSV files to compare stock prices and find percentage differences.")

    st.subheader("Upload CSV Files")
    file1 = st.file_uploader("Upload First BhavCopy CSV File", type=["csv"], key="file1")
    file2 = st.file_uploader("Upload Second BhavCopy CSV File", type=["csv"], key="file2")

    if st.button("Process Files"):
        if file1 is not None and file2 is not None:
            st.info("Processing files... This may take a moment.")
            
            df1 = process_csv(file1)
            df2 = process_csv(file2)

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
                st.error("Failed to process one or both CSV files. Please check the file content and column names.")
        else:
            st.warning("Please upload both CSV files to proceed.")

    st.markdown("---")
    st.markdown("NSE Stock Analysis")
