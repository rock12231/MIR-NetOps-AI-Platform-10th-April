# src/utils/auth.py
import streamlit as st
import os
import requests
import json
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Define API base URL
API_BASE_URL = os.getenv('BACKEND_API_BCHAT_API_BASE_URLASE_URL', 'http://172.178.38.117:8001')
# CHAT_API_BASE_URL:-http://172.178.38.117:8001
def init_session_state():
    """Initialize session state variables"""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "token" not in st.session_state:
        st.session_state.token = None
    logger.debug("Session state initialized.")

def login():
    """Handle user login via API"""
    st.subheader("Login Required")
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login")

        if submitted:
            logger.info(f"Login attempt for user: {username}")
            try:
                # Call the authentication API
                login_url = f"{API_BASE_URL}/api/v1/auth/token"
                response = requests.post(
                    login_url,
                    data={"username": username, "password": password},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    # Extract token from response
                    auth_data = response.json()
                    access_token = auth_data.get("access_token")
                    
                    # Store in session state
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.token = access_token
                    
                    logger.success(f"User '{username}' logged in successfully.")
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    # Handle error responses
                    error_msg = "Invalid credentials"
                    try:
                        error_data = response.json()
                        if "detail" in error_data:
                            error_msg = error_data["detail"]
                    except:
                        pass
                    
                    logger.warning(f"Failed login attempt for user {username}: {error_msg}")
                    st.error(f"Login failed: {error_msg}")
                    
            except Exception as e:
                logger.error(f"Login error: {str(e)}")
                st.error(f"Connection error: {str(e)}")

def logout():
    """Handle user logout"""
    logger.info(f"Logging out user: {st.session_state.get('username', 'Unknown')}")
    keys_to_clear = ["logged_in", "username", "token"]
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