# src/utils/auth.py
import streamlit as st
import os
import requests # Need requests back for API call
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()
# Ensure API_BASE_URL points to your backend
API_BASE_URL = os.getenv("CHAT_API_BASE_URL", "http://backend:8001")

# Remove or comment out hardcoded credentials
# VALID_USERNAME = "mir"
# VALID_PASSWORD = "mir123"

def init_session_state():
    """Initialize session state variables"""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "token" not in st.session_state:
        st.session_state.token = None
    if "username" not in st.session_state:
        st.session_state.username = None
    # logger.debug("Session state initialized.") # Keep if desired

def login():
    """Handle user login by calling the backend API's token endpoint"""
    st.subheader("Login Required")
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login")

        if submitted:
            logger.info(f"Login attempt for user: {username} via backend API.")
            try:
                # --- Call the backend token endpoint ---
                token_endpoint = f"{API_BASE_URL}/api/v1/auth/token"
                logger.debug(f"Calling token endpoint: {token_endpoint}")
                response = requests.post(
                    token_endpoint,
                    # Data format depends on the backend expects (e.g., form data)
                    data={"username": username, "password": password},
                    timeout=15 # Timeout for the login request
                )
                # --- ---

                if response.status_code == 200:
                    # --- Successfully authenticated by backend ---
                    token_data = response.json()
                    if "access_token" not in token_data:
                         logger.error("Backend response missing 'access_token'")
                         st.error("Login failed: Invalid response from authentication server.")
                         return

                    token = token_data["access_token"]
                    st.session_state.logged_in = True
                    st.session_state.token = token # Store the REAL token
                    st.session_state.username = username
                    logger.success(f"User '{username}' logged in successfully via backend.")
                    st.success("Logged in successfully!")
                    st.rerun()
                    # --- ---
                elif response.status_code == 401 or response.status_code == 400: # Handle bad credentials
                     logger.warning(f"Invalid backend login attempt for user: {username} ({response.status_code})")
                     st.error("Invalid username or password.")
                else: # Handle other potential API errors
                    logger.error(f"Backend login failed for user '{username}'. Status: {response.status_code}, Response: {response.text}")
                    st.error(f"Login failed: Server error ({response.status_code}). Please try again later.")

            except requests.exceptions.ConnectionError:
                logger.error(f"Connection error during login: Could not connect to {API_BASE_URL}")
                st.error(f"Connection Error: Unable to reach the authentication server at {API_BASE_URL}.")
            except requests.exceptions.Timeout:
                logger.error("Login request timed out.")
                st.error("Login request timed out. The server took too long to respond.")
            except Exception as e:
                logger.exception("An unexpected error occurred during login:")
                st.error(f"An unexpected error occurred during login: {e}")

def logout():
    """Handle user logout"""
    logger.info(f"Logging out user: {st.session_state.get('username', 'Unknown')}")
    keys_to_clear = ["token", "logged_in", "username"]
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
    if not st.session_state.get("logged_in", False) or not st.session_state.get("token"):
         # Also check if token exists, as it's crucial now
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