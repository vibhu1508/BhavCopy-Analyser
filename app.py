import streamlit as st
from stock_comparison_tab import render_stock_comparison_tab
from new_functionality_tab import render_new_functionality_tab
from corporate_announcements_tab import render_corporate_announcements_tab

st.set_page_config(page_title="NSE Stock Analysis Platform", layout="wide")

tab1, tab2, tab3 = st.tabs(["Stock Comparison", "F/O and Nifty Comparison", "Corporate Announcements"])

with tab1:
    render_stock_comparison_tab()

with tab2:
    render_new_functionality_tab()

with tab3:
    render_corporate_announcements_tab()
