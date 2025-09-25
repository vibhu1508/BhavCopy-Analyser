import streamlit as st
import hashlib

def make_hashes(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def login_form():
    st.subheader("Login to the Application")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username and password:
            # Retrieve stored credentials from st.secrets
            stored_username = st.secrets["credentials"]["username"]
            stored_password_hash = st.secrets["credentials"]["password_hash"]

            if username == stored_username and check_hashes(password, stored_password_hash):
                st.session_state['authenticated'] = True
                st.success("Logged in successfully!")
                st.rerun() # Rerun to hide login form and show app content
            else:
                st.error("Invalid Username or Password")
        else:
            st.warning("Please enter both username and password")

def logout_button():
    if st.sidebar.button("Logout"):
        st.session_state['authenticated'] = False
        st.rerun() # Rerun to show login form
