# Main.py
import streamlit as st
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from loguru import logger
import requests
import json

# Import specific functions needed
from src.utils.auth import init_session_state, login, logout, check_auth

# Define API base URL
API_BASE_URL = os.getenv('BACKEND_API_BASE_URL', 'http://backend-api:8001')

# Add API-based health check function
def health_check():
    try:
        response = requests.get(f"{API_BASE_URL}/system/health")
        
        if response.status_code == 200:
            st.session_state['api_healthy'] = (response.status_code == 200 and response.json().get("status") == "healthy")
            data = response.json()
            return data
            # {"status": "healthy","qdrant_status": "ok","llm_status": "ok"}
        else:
            st.session_state['api_healthy'] = False
            logger.warning(f"Health check failed with status code: {response.status_code}")
            return False
        logger.info(f"API Health Check Result: {st.session_state['api_healthy']}")
        return False
    except Exception as e:
        logger.error(f"Failed to connect to health check API: {str(e)}")
        return False

def get_system_info():
    try:
        response = requests.get(f"{API_BASE_URL}/system/info")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"System info response: {data}")
            return data
            # {"version":"1.0.0","qdrant":{"collections":[{"name":"router_agw_nyc_log_vector","vectors_count":null,"points_count":0,"status":"available"},{"name":"router_dgw_tokyo_log_vector","vectors_count":null,"points_count":0,"status":"available"},{"name":"router_dgw71_pr_re0_log_vector","vectors_count":null,"points_count":131,"status":"available"},{"name":"router_agw_london_log_vector","vectors_count":null,"points_count":0,"status":"available"},{"name":"router_dgw71_flfrd_re0_log_vector","vectors_count":null,"points_count":1,"status":"available"},{"name":"router_fw66_va2_log_vector","vectors_count":null,"points_count":29,"status":"available"},{"name":"router_fw66_dupt_log_vector","vectors_count":null,"points_count":1,"status":"available"},{"name":"router_fw_tokyo_log_vector","vectors_count":null,"points_count":0,"status":"available"},{"name":"router_new_fw67_qcmtl_log_vector","vectors_count":null,"points_count":1,"status":"available"},{"name":"router_agw_tokyo_log_vector","vectors_count":null,"points_count":0,"status":"available"},{"name":"router_dgw70_baal_re0_log_vector","vectors_count":null,"points_count":1,"status":"available"},{"name":"router_vadc_nyc_log_vector","vectors_count":null,"points_count":0,"status":"available"},{"name":"router_fw67_wlfdle_log_vector","vectors_count":null,"points_count":2,"status":"available"},{"name":"router_fw_london_log_vector","vectors_count":null,"points_count":0,"status":"available"},{"name":"router_fw66_wlfdle_log_vector","vectors_count":null,"points_count":2,"status":"available"},{"name":"router_dgw71_grnsbr_re0_log_vector","vectors_count":null,"points_count":1,"status":"available"},{"name":"router_fw67_nbmn_log_vector","vectors_count":null,"points_count":2,"status":"available"},{"name":"router_dgw70_pr_re0_log_vector","vectors_count":null,"points_count":136,"status":"available"},{"name":"router_dgw70_hnsn_re0_log_vector","vectors_count":null,"points_count":1,"status":"available"},{"name":"router_vadc_london_log_vector","vectors_count":null,"points_count":0,"status":"available"},{"name":"router_fw66_ms1_log_vector","vectors_count":null,"points_count":2,"status":"available"},{"name":"router_dgw_nyc_log_vector","vectors_count":null,"points_count":0,"status":"available"},{"name":"router_agw66_ym_log_vector","vectors_count":null,"points_count":8959,"status":"available"},{"name":"router_fw66_ed2_log_vector","vectors_count":null,"points_count":1,"status":"available"},{"name":"router_dgw_london_log_vector","vectors_count":null,"points_count":0,"status":"available"},{"name":"router_fw66_to3_log_vector","vectors_count":null,"points_count":3,"status":"available"},{"name":"router_fw67_va2_log_vector","vectors_count":null,"points_count":17,"status":"available"},{"name":"router_fw67_ms1_log_vector","vectors_count":null,"points_count":4,"status":"available"},{"name":"router_dgw71_rchrd_re0_log_vector","vectors_count":null,"points_count":695,"status":"available"},{"name":"router_new_fw66_qcmtl_log_vector","vectors_count":null,"points_count":1,"status":"available"},{"name":"router_vadc66a_ml02_log_vector","vectors_count":null,"points_count":3807,"status":"available"},{"name":"router_fw67_dupt_log_vector","vectors_count":null,"points_count":1,"status":"available"},{"name":"router_fw67_ed2_log_vector","vectors_count":null,"points_count":1,"status":"available"},{"name":"router_dgw70_slnt_re0_log_vector","vectors_count":null,"points_count":1,"status":"available"},{"name":"router_fw66_nbmn_log_vector","vectors_count":null,"points_count":2,"status":"available"},{"name":"router_fw66_ym_log_vector","vectors_count":null,"points_count":35150,"status":"available"},{"name":"router_vadc_tokyo_log_vector","vectors_count":null,"points_count":0,"status":"available"},{"name":"router_fw_nyc_log_vector","vectors_count":null,"points_count":0,"status":"available"},{"name":"router_fw67_to3_log_vector","vectors_count":null,"points_count":2,"status":"available"}],"status":"available"},"llm":{"model_name":"gemini-2.0-flash","provider":"gemini"}}
        logger.warning(f"Failed to fetch system info with status code: {response.status_code}")
        return {}
    except Exception as e:
        logger.error(f"Failed to connect to system info API: {str(e)}")
        return {}
# Initialize Qdrant client

# --- Page Configuration --- MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="MIR NetOps AI Platform",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
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

# Custom CSS
def load_custom_css():
    st.markdown("""
    <style>
        /* Card styling */
        div.card {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            transition: transform 0.3s, box-shadow 0.3s;
            cursor: pointer;
        }
        div.card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.12);
        }
        div.card h3 {
            margin-top: 0;
            color: #0f52ba;
        }
        div.card img {
            display: block;
            margin: 0 auto 15px auto;
            max-width: 60px;
        }
        div.metric-container {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }
        /* Header styling */
        .main-header {
            color: #0f52ba;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f2f6;
            margin-bottom: 20px;
        }
        /* User welcome message */
        .welcome-message {
            background-color: #e7f2ff;
            border-left: 4px solid #0f52ba;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 25px;
        }
        /* Status indicators */
        .status-success {
            color: #28a745;
            font-weight: bold;
        }
        .status-error {
            color: #dc3545;
            font-weight: bold;
        }
        /* Custom sidebar */
        .sidebar-header {
            padding: 10px;
            text-align: center;
            margin-bottom: 15px;
        }
    </style>
    """, unsafe_allow_html=True)


# Function to create a navigation card
def nav_card(title, icon, description, page_link):
    card_html = f"""
    <div class="card" onclick="window.location.href='{page_link}'">
        <h3><span style="font-size: 24px;">{icon}</span> {title}</h3>
        <p>{description}</p>
    </div>
    """
    return card_html

# Mock data for dashboard summary (replace with real data later)
def get_mock_dashboard_data():
    return {
        "active_devices": 42,
        "alerts_24h": 5,
        "flapping_interfaces": 3,
        "system_health": 92.5,
        "events_chart": [
            {"date": (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d"), "events": 120},
            {"date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"), "events": 155},
            {"date": (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"), "events": 110},
            {"date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"), "events": 185},
            {"date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"), "events": 142},
            {"date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), "events": 168},
            {"date": datetime.now().strftime("%Y-%m-%d"), "events": 60},
        ]
    }

# Main application
def main():
    # Load custom CSS
    load_custom_css()
    
    # Header with logo
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        st.markdown("# 🌐")
    with col_title:
        st.markdown('<h1 class="main-header">MIR NetOps AI Platform</h1>', unsafe_allow_html=True)

    # --- Authentication Check ---
    # If not logged in, display the login form and stop further execution
    if not st.session_state.get("logged_in", False):
        logger.info("User not logged in. Displaying login form.")
        # Add welcome message before login form
        st.markdown("""
        ### Welcome to the Network Monitoring Dashboard
        Please log in to access all features of the platform.
        """)
        login()
        # The login() function now calls st.rerun() on success,
        # so we don't necessarily need st.stop() here, but it ensures
        # nothing below runs until login is successful.
        st.stop()

    # --- Main Content (Only shown if logged in) ---
    logger.info(f"User '{st.session_state.username}' is logged in. Displaying main content.")
    
    # Welcome message
    st.markdown(
        f'<div class="welcome-message">'
        f'<h3>👋 Welcome, {st.session_state.username}!</h3>'
        f'<p>This platform helps you monitor network health, analyze device status, and troubleshoot issues with AI assistance.</p>'
        f'</div>',
        unsafe_allow_html=True
    )
    
    # # Dashboard Summary
    # st.subheader("📊 Dashboard Summary")
    
    # # Get dashboard data
    # dashboard_data = get_mock_dashboard_data()
    
    # # Key metrics in columns
    # col1, col2, col3, col4 = st.columns(4)
    
    # with col1:
    #     st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    #     st.metric("Active Devices", dashboard_data["active_devices"])
    #     st.markdown('</div>', unsafe_allow_html=True)
    
    # with col2:
    #     st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    #     st.metric("Alerts (24h)", dashboard_data["alerts_24h"], delta="2")
    #     st.markdown('</div>', unsafe_allow_html=True)
    
    # with col3:
    #     st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    #     st.metric("Flapping Interfaces", dashboard_data["flapping_interfaces"], delta="-1")
    #     st.markdown('</div>', unsafe_allow_html=True)
    
    # with col4:
    #     st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    #     st.metric("System Health", f"{dashboard_data['system_health']}%", delta="1.5%")
    #     st.markdown('</div>', unsafe_allow_html=True)
    
    # Events chart
    # st.subheader("Weekly Event Trend")
    # events_df = pd.DataFrame(dashboard_data["events_chart"])
    # fig = px.line(
    #     events_df, 
    #     x="date", 
    #     y="events",
    #     title="Network Events (Last 7 Days)",
    #     line_shape="spline",
    #     markers=True
    # )
    # fig.update_layout(
    #     height=300,
    #     margin=dict(l=20, r=20, t=40, b=20),
    #     xaxis_title="",
    #     yaxis_title="Event Count"
    # )
    # st.plotly_chart(fig, use_container_width=True)

    # System Status and Information in columns
    status_col1, status_col2 = st.columns(2)
    
    with status_col1:
        # Check connection to Qdrant
        st.subheader("⚡ System Status")
        with st.spinner("Checking backend connection..."):
            try:
                if health_check():
                    st.markdown('<p><span class="status-success">✅ Connected to Qdrant vector database</span></p>', unsafe_allow_html=True)
                    st.markdown('<p><span class="status-success">✅ Connected to LLM</span></p>', unsafe_allow_html=True)
                    logger.info("Qdrant health check successful.")
                else:
                    st.markdown('<p><span class="status-error">❌ Failed to connect to Qdrant vector database</span></p>', unsafe_allow_html=True)
                    st.markdown('<p><span class="status-error">❌ Failed to connect to LLM</span></p>', unsafe_allow_html=True)
                    logger.error("Qdrant health check failed.")
            except Exception as e:
                st.markdown(f'<p><span class="status-error">❌ Error connecting to Qdrant:</span> {e}</p>', unsafe_allow_html=True)
                logger.exception("Exception during Qdrant health check.")
    
    with status_col2:
        # Check system information
        st.subheader("⚡ System Information")
        with st.spinner("Fetching system info..."):
            try:
                system_info = get_system_info()
                if system_info:
                    st.markdown('<p><span class="status-success">✅ Version : '+system_info["version"]+'</span></p>', unsafe_allow_html=True)
                    st.markdown('<p><span class="status-success">✅ Qdrant Status : '+ system_info["qdrant"]["status"]+'</span></p>', unsafe_allow_html=True)
                    st.markdown('<p><span class="status-success">✅ Qdrant Collections : '+ str(len(system_info["qdrant"]["collections"])) +'</span></p>', unsafe_allow_html=True)
                    st.markdown('<p><span class="status-success">✅ LLM Model : '+ system_info["llm"]["model_name"] +' Provider : '+ system_info["llm"]["provider"]+')</span></p>', unsafe_allow_html=True)
                    logger.info("System info fetched successfully.")
                else:
                    st.markdown('<p><span class="status-error">❌ Failed to fetch system info</span></p>', unsafe_allow_html=True)
                    logger.error("Failed to fetch system info.")
            except Exception as e:
                st.markdown(f'<p><span class="status-error">❌ Error fetching system info:</span> {e}</p>', unsafe_allow_html=True)
                logger.exception("Exception during system info fetch.")

    # Navigation Cards
    st.subheader("🧭 Dashboard Navigation")
    
    # First row of cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            nav_card(
                "Network Overview", 
                "🌍", 
                "Get a high-level view of your entire network with topology maps, health metrics, and location-based analysis.",
                "pages/1_Network_Overview.py"
            ), 
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            nav_card(
                "Devices Dashboard", 
                "📊", 
                "Analyze device status, event timelines, severity distributions, and track network activity patterns.",
                "pages/2_Devices_Dashboard.py"
            ), 
            unsafe_allow_html=True
        )
    
    # Second row of cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            nav_card(
                "Interface Monitoring", 
                "🔌", 
                "Detect flapping interfaces, analyze stability metrics, and troubleshoot network connectivity issues.",
                "pages/3_Interface_Monitoring.py"
            ), 
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            nav_card(
                "AI Chatbot", 
                "🤖", 
                "Get instant insights and answers about your network through a conversational AI assistant.",
                "pages/4_Chatbot.py"
            ), 
            unsafe_allow_html=True
        )
    
    # Third row - single card
    st.markdown(
        nav_card(
            "AI Summary", 
            "🧠", 
            "Generate AI-powered summaries and analyses of network logs to quickly understand system status and issues.",
            "pages/5_AI_Summary.py"
        ), 
        unsafe_allow_html=True
    )

    # # Quick links
    # st.sidebar.markdown("### 🔗 Quick Links")
    # st.sidebar.page_link("pages/1_Network_Overview.py", label="🌍 Network Overview", icon="🌍")
    # st.sidebar.page_link("pages/2_Devices_Dashboard.py", label="📊 Devices Dashboard", icon="📊")
    # st.sidebar.page_link("pages/3_Interface_Monitoring.py", label="🔌 Interface Monitoring", icon="🔌")
    # st.sidebar.page_link("pages/4_Chatbot.py", label="🤖 AI Chatbot", icon="🤖")
    # st.sidebar.page_link("pages/5_ai_summary.py", label="🧠 AI Summary", icon="🧠")

    # --- Sidebar for Logout and User Info ---
    with st.sidebar:
        st.markdown('<div class="sidebar-header">', unsafe_allow_html=True)
        st.header("👤 User Profile")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown(f"""
        **Username:** {st.session_state.username}
        
        **Role:** Network Administrator
        
        **Last Login:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
        """)
        
        # Add separator
        st.markdown("---")
        
        # System info
        st.markdown("### 🖥️ System Info")
        st.markdown(f"""
        **Version:** 1.2.0
        
        **Database:** {'Connected ✅' if health_check() else 'Disconnected ❌'}
        
        **Last Update:** {(datetime.now() - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M")}
        """)
        
        st.markdown("---")
        
        # Logout button with styling
        if st.button("🚪 Logout", type="primary"):
            logout() # logout() handles state clearing and rerun

        st.caption("© 2023 MIR Networks")

if __name__ == "__main__":
    main()