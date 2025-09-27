import streamlit as st
import pandas as pd
from datetime import date, timedelta
from bsescraper import bseindia_apiScraper # Assuming bsescraper.py is in the same directory

# --- Helper Functions (moved from run_scraper.py) ---
@st.cache_data
def get_bse_scrip_codes(file_path='bse_scrip_codes.csv'):
    """Loads BSE scrip codes from a CSV file."""
    try:
        df = pd.read_csv(file_path)
        if 'Scrip Code' in df.columns and 'Company Name' in df.columns:
            # Create a dictionary for easy lookup: Company Name -> Scrip Code
            return df.set_index('Company Name')['Scrip Code'].astype(str).to_dict()
        else:
            st.error(f"Error: 'Scrip Code' or 'Company Name' column not found in {file_path}")
            return {}
    except FileNotFoundError:
        st.error(f"Error: {file_path} not found. Please ensure rediff_scraper.py has been run.")
        return {}
    except Exception as e:
        st.error(f"Error loading scrip codes: {e}")
        return {}

@st.cache_data
def scrape_company_wise(scrip_codes_to_scrape, days_back=1, print_msgs=False):
    """
    Scrapes corporate announcements for a list of scrip codes.
    scrip_codes_to_scrape: A list of scrip codes (strings).
    days_back: Number of days to look back for announcements for each company.
    """
    all_announcements = []
    progress_text = "Scraping company-wise announcements. Please wait."
    my_bar = st.progress(0, text=progress_text)

    for i, scrip_code in enumerate(scrip_codes_to_scrape):
        my_bar.progress((i + 1) / len(scrip_codes_to_scrape), text=f"Scraping {scrip_code}...")
        q_params = {'strScrip': scrip_code, 'printMsgs': print_msgs}
        result = bseindia_apiScraper(searchDate=days_back, qParams=q_params)
        if result and result['data']:
            for item in result['data']:
                item['Scrip_Code_Searched'] = scrip_code
            all_announcements.extend(result['data'])
        elif result['status'] == 'error' and print_msgs:
            st.warning(f"Error scraping for {scrip_code}: {result['msg']}")
    my_bar.empty()
    return pd.DataFrame(all_announcements)

@st.cache_data
def scrape_day_wise(start_date, end_date, scrip_code=None, print_msgs=False):
    """
    Scrapes corporate announcements day-wise for a given date range, optionally filtered by scrip code.
    start_date, end_date: datetime.date objects.
    scrip_code: Optional. A single scrip code string to filter by.
    """
    all_announcements = []
    current_date = start_date
    total_days = (end_date - start_date).days + 1
    progress_text = "Scraping day-wise announcements. Please wait."
    my_bar = st.progress(0, text=progress_text)
    
    day_count = 0
    while current_date <= end_date:
        day_count += 1
        my_bar.progress(day_count / total_days, text=f"Scraping for {current_date.isoformat()}...")
        q_params = {'printMsgs': print_msgs}
        if scrip_code:
            q_params['strScrip'] = scrip_code
        
        result = bseindia_apiScraper(searchDate=current_date, qParams=q_params)
        if result and result['data']:
            for item in result['data']:
                item['Search_Date'] = current_date.isoformat()
                if scrip_code:
                    item['Scrip_Code_Searched'] = scrip_code
            all_announcements.extend(result['data'])
        elif result['status'] == 'error' and print_msgs:
            st.warning(f"Error scraping for {current_date.isoformat()} (Scrip: {scrip_code if scrip_code else 'All'}): {result['msg']}")
        
        current_date += timedelta(days=1)
    my_bar.empty()
    return pd.DataFrame(all_announcements)

# --- Streamlit UI ---
def render_bse_announcements_tab():
    st.header("BSE Corporate Announcements")

    @st.cache_data
    def get_bse_scrip_codes_capitalized(file_path='bse_scrip_codes.csv'):
        """Loads BSE scrip codes from a CSV file and returns a dict with capitalized company names."""
        try:
            df = pd.read_csv(file_path)
            if 'Scrip Code' in df.columns and 'Company Name' in df.columns:
                # Create a dictionary: CAPITALIZED Company Name -> Scrip Code
                return df.set_index(df['Company Name'].str.upper())['Scrip Code'].astype(str).to_dict()
            else:
                st.error(f"Error: 'Scrip Code' or 'Company Name' column not found in {file_path}")
                return {}
        except FileNotFoundError:
            st.error(f"Error: {file_path} not found. Please ensure rediff_scraper.py has been run.")
            return {}
        except Exception as e:
            st.error(f"Error loading scrip codes: {e}")
            return {}

    bse_scrip_codes_dict = get_bse_scrip_codes_capitalized()
    company_names = sorted(bse_scrip_codes_dict.keys()) if bse_scrip_codes_dict else []

    st.subheader("Filter by Date Range")
    
    # Date Range Selection
    today = date.today()
    default_start_date = today - timedelta(days=7)
    start_date = st.date_input("Start Date", default_start_date, key="bse_start_date")
    end_date = st.date_input("End Date", today, key="bse_end_date")

    # Company Selection
    selected_company_name = st.selectbox(
        "Select Company (Optional)", 
        ['ALL COMPANIES'] + company_names,
        key="bse_company_select"
    )
    selected_scrip_code = None
    if selected_company_name != 'ALL COMPANIES':
        selected_scrip_code = bse_scrip_codes_dict.get(selected_company_name)
        st.write(f"Selected Scrip Code: {selected_scrip_code}")

    # Removed print_msgs checkbox as per user request
    print_msgs = False 

    if st.button("Fetch BSE Reports", key="bse_scrape_button"):
        if start_date > end_date:
            st.error("Error: Start date cannot be after end date.")
        else:
            with st.spinner("Scraping in progress..."):
                if selected_company_name == 'ALL COMPANIES':
                    df_results = scrape_day_wise(start_date, end_date, print_msgs=print_msgs)
                else:
                    df_results = scrape_day_wise(start_date, end_date, scrip_code=selected_scrip_code, print_msgs=print_msgs)
                
                if not df_results.empty:
                    st.success(f"Scraped {len(df_results)} announcements.")
                    
                    # Create 'View Report' link column
                    # Convert 'News_submission_dt' to datetime objects for comparison
                    # Handle potential errors during conversion by coercing invalid dates to NaT
                    df_results['News_submission_dt_parsed'] = pd.to_datetime(df_results['News_submission_dt'], errors='coerce').dt.date

                    # Define the threshold date for AttachLive (today and two days back)
                    threshold_date = today - timedelta(days=2)

                    # Apply row-wise logic to determine the correct attachment URL
                    def get_attachment_url(row):
                        if pd.notna(row['ATTACHMENTNAME']):
                            if pd.notna(row['News_submission_dt_parsed']) and row['News_submission_dt_parsed'] >= threshold_date:
                                return f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{row['ATTACHMENTNAME']}"
                            else:
                                return f"https://www.bseindia.com/xml-data/corpfiling/AttachHis/{row['ATTACHMENTNAME']}"
                        return None

                    df_results['View Report'] = df_results.apply(get_attachment_url, axis=1)

                    # Drop the temporary parsed date column
                    df_results.drop(columns=['News_submission_dt_parsed'], inplace=True, errors='ignore')
                    
                    # Rename columns as per user request
                    df_results.rename(columns={
                        'SLONGNAME': 'Company Name',
                        'CATEGORYNAME': 'Announcement Type',
                        'News_submission_dt': 'Timestamp',
                        'HEADLINE': 'Subject'
                    }, inplace=True)

                    # Filter and display specific columns
                    display_columns = ['ANNOUNCEMENTNAME', 'Company Name', 'Announcement Type', 'Subject', 'Timestamp', 'View Report']
                    # Ensure all display_columns exist in df_results before selecting
                    existing_columns = [col for col in display_columns if col in df_results.columns]
                    
                    st.dataframe(df_results[existing_columns],
                                 column_config={"View Report": st.column_config.LinkColumn("View Report", display_text="View Report")})
                    
                    # Option to download
                    csv_data = df_results.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Data as CSV",
                        data=csv_data,
                        file_name="bse_announcements.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("No announcements found for the selected criteria.")
