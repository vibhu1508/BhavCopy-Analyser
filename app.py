import streamlit as st
from stock_comparison_tab import render_stock_comparison_tab
from new_functionality_tab import render_new_functionality_tab
from corporate_announcements_tab import render_corporate_announcements_tab
from bse_announcements_tab import render_bse_announcements_tab # Import BSE announcements tab
from auth import login_form, logout_button # Import authentication functions

st.set_page_config(page_title="NSE Stock Analysis Platform", layout="wide")

# Initialize authentication status
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    login_form()
else:
    logout_button() # Display logout button in sidebar when authenticated
    tab1, tab2, tab3 = st.tabs(["Stock Comparison", "F/O and Nifty Comparison", "Corporate Announcements"])

    with tab1:
        render_stock_comparison_tab()

    with tab2:
        render_new_functionality_tab()

    with tab3:
        nse_tab, bse_tab = st.tabs(["NSE Corporate Announcements", "BSE Corporate Announcements"])
        with nse_tab:
            render_corporate_announcements_tab()
        with bse_tab:
            render_bse_announcements_tab()
