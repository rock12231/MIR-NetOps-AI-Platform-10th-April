# src/utils/auth.py
import streamlit as st
import os
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Hardcoded credentials since we don't have a backend auth API
VALID_USERNAME = "mir"
VALID_PASSWORD = "mir123"

def init_session_state():
    """Initialize session state variables"""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = None
    logger.debug("Session state initialized.")

def login():
    """Handle user login with hardcoded credentials"""
    st.subheader("Login Required")
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login")

        if submitted:
            logger.info(f"Login attempt for user: {username}")
            if username == VALID_USERNAME and password == VALID_PASSWORD:
                st.session_state.logged_in = True
                st.session_state.username = username
                logger.success(f"User '{username}' logged in successfully.")
                st.success("Logged in successfully!")
                st.rerun()
            else:
                logger.warning(f"Invalid login attempt for user: {username}")
                st.error("Invalid username or password.")

def logout():
    """Handle user logout"""
    logger.info(f"Logging out user: {st.session_state.get('username', 'Unknown')}")
    keys_to_clear = ["logged_in", "username"]
    # Optionally clear other session data
    # keys_to_clear.extend(['messages', 'welcome_shown', etc.])
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.success("Logged out successfully!")
    st.rerun()

def check_auth(show_warning=True):
    """
    Check if user is authenticated.
    If not, optionally display a warning and stop the page execution.
    """
    init_session_state()
    logger.debug(f"Checking authentication status: logged_in={st.session_state.get('logged_in', False)}")
    if not st.session_state.get("logged_in", False):
        if show_warning:
            st.warning("🔒 Please login from the main page to access this feature.")
        st.stop()

def get_current_username():
    """Returns the logged-in username or None if not logged in."""
    if st.session_state.get("logged_in", False):
        return st.session_state.get("username")
    return None

# Helper function to get the token for API calls
def get_auth_header():
    """Returns the Authorization header dictionary if logged in, else None."""
    if st.session_state.get("logged_in", False) and st.session_state.get("token"):
        return {"Authorization": f"Bearer {st.session_state['token']}"}
    else:
        logger.warning("Attempted to get auth header when not logged in or token is missing.")
        return None # Or raise an error? Returning None is safer for optional auth routes.