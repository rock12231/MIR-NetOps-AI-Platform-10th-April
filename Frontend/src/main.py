# Main.py
"""
Network Monitoring Dashboard - Main Application.
Multipage Streamlit application for monitoring network devices.
"""

import streamlit as st
import os
from loguru import logger
from src.utils.qdrant_client import get_qdrant_client, health_check
# Import specific functions needed
from src.utils.auth import init_session_state, login, logout, check_auth

# --- Page Configuration --- MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="MIR NetOps AI Platform",
    page_icon="🌐",
    layout="wide"
)

# Initialize session state - This should be called early
init_session_state()

# Configure logging
os.makedirs('logs', exist_ok=True)
# Configure Loguru to log to a file
log_file_path = os.path.join("logs", "streamlit_app_{time}.log")
logger.add(log_file_path, rotation="10 MB", retention="7 days", level="INFO", format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}")
# logger.add(lambda _: st.error(_.getMessage()), level="ERROR") # Streamlit handler for errors
# logger.add(lambda _: st.warning(_.getMessage()), level="WARNING") # Streamlit handler for warnings
# Reduce console noise for DEBUG messages unless needed
# logger.add(sys.stderr, level="INFO") # Control console level if needed

logger.info("Main application started.")

# Main application
def main():
    st.title("🌐 MIR NetOps AI Platform")

    # --- Authentication Check ---
    # If not logged in, display the login form and stop further execution
    if not st.session_state.get("logged_in", False):
        logger.info("User not logged in. Displaying login form.")
        login()
        # The login() function now calls st.rerun() on success,
        # so we don't necessarily need st.stop() here, but it ensures
        # nothing below runs until login is successful.
        st.stop()

    # --- Main Content (Only shown if logged in) ---
    logger.info(f"User '{st.session_state.username}' is logged in. Displaying main content.")
    st.markdown(f"""
    Welcome, **{st.session_state.username}**, to the Network Monitoring Dashboard for analyzing router logs and interface status.

    This platform allows you to:
    - Monitor overall network health and activity (**Network Overview**)
    - Analyze device status, events, and severity (**Devices Dashboard**)
    - Investigate interface stability and flapping issues (**Interface Monitoring**)
    - Interact with an AI Chatbot for network insights (**AI Chatbot**)
    - Generate AI-driven summaries and analyses of logs (**AI Summary**)

    Use the sidebar (**👈**) to navigate between different dashboard components or to log out.
    """)

    # Check connection to Qdrant
    st.subheader("System Status")
    with st.spinner("Checking database connection..."):
        try:
            if health_check():
                st.success("✅ Successfully connected to Qdrant vector database.")
                logger.info("Qdrant health check successful.")
            else:
                st.error("❌ Failed to connect to Qdrant database. Data fetching may fail.")
                logger.error("Qdrant health check failed.")
        except Exception as e:
            st.error(f"❌ Error connecting to Qdrant: {e}")
            logger.exception("Exception during Qdrant health check.")


    # Display dashboard components links (These should navigate to the respective pages)
    st.subheader("Dashboard Components")
    st.page_link("pages/1_Network_Overview.py", label="🌍 Network Overview", icon="🌍")
    st.page_link("pages/2_Devices_Dashboard.py", label="📊 Devices Dashboard", icon="📊")
    st.page_link("pages/3_Interface_Monitoring.py", label="🔌 Interface Monitoring", icon="🔌")
    st.page_link("pages/4_Chatbot.py", label="🤖 AI Chatbot", icon="🤖")
    st.page_link("pages/5_ai_summary.py", label="🧠 AI Summary", icon="🧠")

    # Display dashboard components
    # st.markdown("## Dashboard Components")
    
    # col1, col2, col3, col4 = st.columns(4)
    
    # with col1:
    #     st.markdown("""
    #     ### 🌍 Network Overview
        
    #     High-level insights across the entire network:
    #     - Network topology visualization
    #     - Global performance metrics
    #     - Location health summary
    #     - Event trend analysis
        
    #     [Open Network Overview](pages/1_Network_Overview.py)
    #     """)
    
    # with col2:
    #     st.markdown("""
    #     ### 📊 Devices Dashboard
        
    #     Overview of network devices, health, and activity metrics:
    #     - Device status monitoring
    #     - Event timelines and distributions
    #     - Severity analysis
        
    #     [Open Dashboard](pages/2_Devices_Dashboard.py)
    #     """)
    
    # with col3:
    #     st.markdown("""
    #     ### 🔌 Interface Monitoring
        
    #     Focused analysis of network interfaces:
    #     - Flapping interface detection
    #     - Interface stability scoring
    #     - Detailed timeline analysis
        
    #     [Open Interface Monitoring](pages/3_Interface_Monitoring.py)
    #     """)
        
    # with col4:
    #     st.markdown("""
    #     ### 🤖 AI Chatbot
        
    #     Interactive AI assistant for network analysis:
    #     - Natural language queries
    #     - Real-time network insights
    #     - Context-aware responses
        
    #     [Open Chatbot](pages/4_Chatbot.py)
    #     """)
        

    # --- Sidebar for Logout ---
    with st.sidebar:
        st.header("User")
        st.write(f"👤 Logged in as: **{st.session_state.username}**")
        if st.button("Logout"):
            logout() # logout() handles state clearing and rerun

if __name__ == "__main__":
    main()