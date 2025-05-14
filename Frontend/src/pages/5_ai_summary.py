# pages/5_ai_summary.py
import streamlit as st  # Keep streamlit import first
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
import requests
from loguru import logger
from typing import Dict, Any
import os
from src.utils.auth import check_auth, init_session_state, logout  # Added logout for sidebar

# --- Page Configuration --- MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="5_AI Summary",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Authentication Check ---
init_session_state()  # Initialize session state
check_auth()
logger.info(f"User '{st.session_state.username}' accessed AI Summary page.")

# Backend API URL for system health check
API_BASE_URL = os.getenv('BACKEND_API_BASE_URL', 'http://backend-api:8001')

# Function to check health status
def health_check():
    """
    Check system health by calling the health API.
    
    Returns:
        bool: True if system is healthy, False otherwise
    """
    try:
        response = requests.get(f"{API_BASE_URL}/system/health")
        if response.status_code == 200:
            data = response.json()
            return data.get("status") == "healthy"
        return False
    except:
        logger.error("Failed to connect to health check API")
        return False

# Custom CSS for sidebar styling
def load_custom_css():
    st.markdown("""
    <style>
        /* Custom sidebar styling */
        .sidebar-header {
            padding: 10px;
            text-align: center;
            margin-bottom: 15px;
        }
        .sidebar-section {
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
    </style>
    """, unsafe_allow_html=True)

# Load custom CSS
load_custom_css()

# --- Configuration ---
METADATA_PATH = os.getenv('METADATA_PATH', 'data/qdrant_db_metadata.json')
CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))
API_TIMEOUT = 180

# --- Metadata Loading ---
@st.cache_data(ttl=CACHE_TTL)
def load_metadata():
    default_meta = get_default_metadata()
    try:
        if os.path.exists(METADATA_PATH):
            with open(METADATA_PATH, 'r') as f:
                metadata = json.load(f)
            if not isinstance(metadata, dict):
                logger.error("Metadata file content is not a dictionary.")
                return default_meta

            required_keys = ["agw", "dgw", "fw", "vadc"]
            default_sub_keys = ["devices", "locations", "categories", "event_types", "interfaces"]
            type_specific_sub_keys = {"fw": ["processes"]}

            for key in required_keys:
                if key not in metadata:
                    logger.warning(f"Metadata missing device type key: '{key}'. Using default.")
                    metadata[key] = default_meta.get(key, {})
                elif not isinstance(metadata[key], dict):
                    logger.warning(f"Metadata key '{key}' is not a dictionary. Using default.")
                    metadata[key] = default_meta.get(key, {})

            for dev_type in required_keys:
                expected_sub_keys = default_sub_keys + type_specific_sub_keys.get(dev_type, [])
                current_sub_keys = list(metadata[dev_type].keys())
                for sub_key in current_sub_keys:
                    if not isinstance(metadata[dev_type][sub_key], list):
                        is_expected = sub_key in expected_sub_keys
                        if is_expected:
                            logger.warning(f"Metadata key '{dev_type}.{sub_key}' is not a list. Resetting.")
                        metadata[dev_type][sub_key] = []
                for expected_key in expected_sub_keys:
                    if expected_key not in metadata[dev_type]:
                        metadata[dev_type][expected_key] = []

            if "collections" not in metadata or not isinstance(metadata["collections"], list):
                metadata["collections"] = []
            logger.info(f"Successfully loaded metadata from {METADATA_PATH}")
            return metadata
        else:
            logger.warning(f"Metadata file {METADATA_PATH} not found. Using default.")
            return default_meta
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing metadata file {METADATA_PATH}: {str(e)}")
        return default_meta
    except Exception as e:
        logger.error(f"Error loading metadata: {str(e)}")
        return default_meta

def get_default_metadata():
    logger.info("Using default metadata configuration")
    return {
        "collections": [],
        "agw": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": []},
        "dgw": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": []},
        "fw": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": [], "processes": []},
        "vadc": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": []}
    }

# --- API Interaction Functions ---
def call_api(endpoint: str, payload: dict) -> dict:
    url = f"{API_BASE_URL}/api/v1{endpoint}"
    try:
        payload_keys_log = {k: type(v) for k, v in payload.items()}
        logger.info(f"Calling API endpoint: {url} with payload keys/types: {payload_keys_log}")
        response = requests.post(url, json=payload, timeout=API_TIMEOUT)
        response.raise_for_status()
        logger.info(f"API call successful (Status: {response.status_code})")
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        try:
            error_details = response.json()
            detail_msg = error_details.get('detail', response.text)
        except json.JSONDecodeError:
            detail_msg = response.text
        logger.error(f"API Error ({response.status_code}): {detail_msg}")
        return {"status": "error", "message": f"API Error ({response.status_code}): {detail_msg}"}
    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling API {url} after {API_TIMEOUT} seconds.")
        return {"status": "error", "message": f"Request timed out after {API_TIMEOUT} seconds"}
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Connection error calling API {url}: {conn_err}")
        logger.error(f"Could not connect to the analysis API at {API_BASE_URL}.")
        return {"status": "error", "message": f"Connection Error: {conn_err}"}
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Error calling API {url}: {req_err}")
        return {"status": "error", "message": f"Request Error: {req_err}"}
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON response from API {url}. Status: {response.status_code}, Response: {response.text}")
        return {"status": "error", "message": "Invalid JSON response from API", "raw_response": response.text}
    except Exception as e:
        logger.error(f"Unexpected error during API call to {url}: {e}", exc_info=True)
        return {"status": "error", "message": f"Unexpected Error: {e}"}

# --- Function to Display API Analysis Results ---
# ... (keep the existing display_api_analysis function - no changes needed here) ...
def display_api_analysis(data: Dict[str, Any]):
    if not isinstance(data, dict):
        logger.error("Invalid analysis data received (expected a dictionary).")
        st.json(data)
        return

    status = data.get("status")
    collection_name_disp = data.get('collection_name', 'N/A')
    log_count_disp = data.get('log_count', None)
    sample_size = data.get('sample_size', None)

    if status == "success" and "analysis" in data:
        analysis = data.get("analysis")
        if not isinstance(analysis, dict):
            logger.error(f"Invalid 'analysis' structure in API response for {collection_name_disp} (expected a dictionary).")
            st.json(data)
            return

        st.markdown("---")
        if sample_size is not None and log_count_disp is None:
            st.caption(f"Analysis based on {sample_size} log sample(s) retrieved.")
        elif log_count_disp is not None:
            log_count_text = "1 log" if log_count_disp == 1 else f"{log_count_disp} logs"
            st.caption(f"Analysis based on {log_count_text} provided.")
        else:
            st.caption("Analysis details provided below.")

        st.markdown('**Analysis Summary**')
        summary_text = analysis.get('summary', '').strip()
        st.markdown(f"> {summary_text if summary_text else '_No summary provided._'}")

        if sample_size is not None:
            st.markdown("**Sampled Logs Used in Summary**")
            sampled_logs = data.get("sampled_logs", [])
            if isinstance(sampled_logs, list) and sampled_logs:
                log_data = []
                for log in sampled_logs:
                    if not isinstance(log, dict):
                        continue
                    log_entry = {
                        "Log ID": log.get("_qdrant_id", "N/A"),
                        "Timestamp": log.get("_standardized_timestamp_iso", log.get("timestamp", "N/A")),
                        "Device": log.get("device", "N/A"),
                        "Raw Log": log.get("raw_log", log.get("message", "N/A"))[:100] + ("..." if len(log.get("raw_log", log.get("message", ""))) > 100 else ""),
                        "Severity": log.get("severity", "N/A"),
                        "Category": log.get("category", "N/A")
                    }
                    log_data.append(log_entry)
                if log_data:
                    df_logs = pd.DataFrame(log_data)
                    st.dataframe(df_logs, hide_index=True, use_container_width=True)
                    with st.expander("Log Details"):
                        for i, log in enumerate(sampled_logs):
                            if not isinstance(log, dict):
                                continue
                            log_id = log.get("_qdrant_id", f"Log {i+1}")
                            preview = log.get("raw_log", log.get("message", "No message"))[:50]
                            st.markdown(f"**Log {i+1}: {log_id}** - `{preview}...`")
                            st.json(log)
                else:
                    st.warning("Sampled logs data present but could not be processed (invalid format).")
            elif isinstance(sampled_logs, list) and not sampled_logs:
                st.info("No logs were sampled for this summary (likely due to filters or empty collection).")
            else:
                logger.warning("Sampled logs data is missing or not in the expected list format.")
                st.warning("Sampled logs data is unavailable or not in the expected format.")

        tab_titles = ["🔍 Anomalies", "✅ Normal Patterns", "💡 Recommendations", "ℹ️ Metadata", "📦 Raw API Data"]
        result_tabs = st.tabs(tab_titles)

        with result_tabs[0]:
            anomalies_list = analysis.get("anomalies", [])
            if isinstance(anomalies_list, list) and anomalies_list:
                st.markdown(f"**Detected Anomalies ({len(anomalies_list)}):**")
                valid_anomalies = [anom for anom in anomalies_list if isinstance(anom, dict)]
                if len(valid_anomalies) < len(anomalies_list):
                    logger.warning("Some items in the 'anomalies' list were not valid dictionaries and were ignored.")
                anomalies_data = []
                for anom in valid_anomalies:
                    anomalies_data.append({
                        "Severity": anom.get("severity", "N/A"),
                        "Review": "Yes" if anom.get("requires_review", False) else "No",
                        "Description": anom.get("description", "N/A"),
                        "Log ID": anom.get("log_id", "N/A"),
                        "Device": anom.get("device", "N/A"),
                        "Timestamp": anom.get("timestamp", "N/A"),
                        "Category": anom.get("category", "N/A"),
                    })
                if anomalies_data:
                    df_anom = pd.DataFrame(anomalies_data)
                    st.dataframe(df_anom, hide_index=True, use_container_width=True)
                elif anomalies_list:
                    st.warning("Anomaly data found but could not be processed (invalid format).")
                    st.json(anomalies_list)
                st.markdown("**Anomaly Details:**")
                for i, anom in enumerate(valid_anomalies):
                    severity = anom.get("severity", "Medium")
                    severity_class = str(severity).lower()
                    desc_preview = str(anom.get('description', 'Details'))
                    exp_title = f"Anomaly {i+1}: {desc_preview[:80]}{'...' if len(desc_preview)>80 else ''}"
                    with st.expander(exp_title):
                        st.markdown(f"**Severity:** <span class='severity-{severity_class}'>{severity}</span>", unsafe_allow_html=True)
                        st.markdown(f"**Requires Review:** {'**Yes**' if anom.get('requires_review') else 'No'}")
                        reasoning = anom.get('reasoning', '').strip()
                        st.markdown(f"**Reasoning:** {reasoning if reasoning else '_No reasoning provided._'}")
                        st.markdown(f"**Log ID:** `{anom.get('log_id', 'N/A')}`")
                        st.markdown(f"**Timestamp:** `{anom.get('timestamp', 'N/A')}`")
                        st.markdown(f"**Device:** `{anom.get('device', 'N/A')}`")
                        st.markdown(f"**Location:** `{anom.get('location', 'N/A')}`")
                        st.markdown(f"**Category:** `{anom.get('category', 'N/A')}`")
            elif isinstance(anomalies_list, list) and not anomalies_list:
                st.info("✅ No anomalies were identified by the AI.")
            else:
                logger.warning("Anomaly data is missing or not in the expected list format.")
                st.warning("Anomaly data is missing or not in the expected list format.")

        with result_tabs[1]:
            normal_patterns = analysis.get("normal_patterns", [])
            if isinstance(normal_patterns, list) and normal_patterns:
                st.markdown("**Observed Normal Patterns:**")
                valid_patterns = [p for p in normal_patterns if isinstance(p, str)]
                for pattern in valid_patterns:
                    st.markdown(f"- {pattern}")
                if len(valid_patterns) < len(normal_patterns):
                    logger.warning("Some items in 'normal_patterns' were ignored due to invalid format (not strings).")
            elif isinstance(normal_patterns, list) and not normal_patterns:
                st.info("No specific normal patterns were listed by the AI.")
            else:
                logger.warning("Normal patterns data is missing or not in the expected list format.")
                st.warning("Normal patterns data is missing or not in the expected list format.")

        with result_tabs[2]:
            recommendations = analysis.get("recommendations", [])
            if isinstance(recommendations, list) and recommendations:
                st.markdown("**AI Recommendations:**")
                valid_recs = [r for r in recommendations if isinstance(r, str)]
                for i, rec in enumerate(valid_recs):
                    st.markdown(f"{i+1}. {rec}")
                if len(valid_recs) < len(recommendations):
                    logger.warning("Some items in 'recommendations' were ignored due to invalid format (not strings).")
            elif isinstance(recommendations, list) and not recommendations:
                st.info("No recommendations were provided by the AI.")
            else:
                logger.warning("Recommendations data is missing or not in the expected list format.")
                st.warning("Recommendations data is missing or not in the expected list format.")

        with result_tabs[3]:
            st.markdown("**Analysis Metadata:**")
            meta_devices = analysis.get('devices_analyzed', [])
            meta_locations = analysis.get('locations_analyzed', [])
            time_period = analysis.get("time_period")
            st.write(f"**Devices Analyzed:** {', '.join(meta_devices) if isinstance(meta_devices, list) else 'N/A'}")
            st.write(f"**Locations Analyzed:** {', '.join(meta_locations) if isinstance(meta_locations, list) else 'N/A'}")
            start_time_str = "N/A"
            end_time_str = "N/A"
            if isinstance(time_period, dict):
                start_time_str = time_period.get('start') or "N/A"
                end_time_str = time_period.get('end') or "N/A"
                if isinstance(start_time_str, str) and 'T' in start_time_str: start_time_str = start_time_str.replace('T', ' ')
                if isinstance(end_time_str, str) and 'T' in end_time_str: end_time_str = end_time_str.replace('T', ' ')
            st.write(f"**Analysis Time Period:** {start_time_str} to {end_time_str}")
            req_time_period = data.get("request_time_period")
            if isinstance(req_time_period, dict):
                req_start = req_time_period.get('start') or "N/A"
                req_end = req_time_period.get('end') or "N/A"
                if isinstance(req_start, str) and 'T' in req_start: req_start = req_start.replace('T', ' ')
                if isinstance(req_end, str) and 'T' in req_end: req_end = req_end.replace('T', ' ')
                st.write(f"**Requested Time Filter:** {req_start} to {req_end}")

        with result_tabs[4]:
            st.markdown("**Raw API Response (JSON):**")
            st.json(data)

    elif status == "error":
        error_message = data.get("message", "An unknown error occurred.")
        st.error(f"API Error: {error_message}") # Display the error message clearly
        if data:
            with st.expander("Raw Error Data from API"):
                st.json(data)
        else:
            st.warning("No further error details available from API.")
    else:
        logger.error(f"Received an unexpected response status ('{status}') from the API for {collection_name_disp}.")
        st.error("Received an unexpected response from the API.") # Generic error for unexpected status
        with st.expander("Raw Response Data"):
            st.json(data)

# --- Sidebar Controls ---
# ... (keep the existing render_sidebar function - no changes needed here) ...
def render_sidebar():
    # User Profile Section
    with st.sidebar:
        st.markdown('<div class="sidebar-header">', unsafe_allow_html=True)
        st.header("👤 User Profile")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown(f"""
        **Username:** {st.session_state.username}
        
        **Role:** Network Administrator
        
        **Last Login:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
        """)
        
        st.markdown("---")
    
    st.sidebar.header("⚙️ AI Summary Controls")

    # --- Collection Selection ---
    st.sidebar.subheader("📍 Collection Selection")
    metadata = load_metadata()
    device_types = sorted([key for key in metadata if key not in ["collections"]])
    selected_device_type = st.sidebar.selectbox(
        "Device Type:",
        options=device_types,
        key="ai_device_type_select",
        index=0 if device_types else None
    )

    devices_for_type = []
    locations_for_type = []
    if selected_device_type and selected_device_type in metadata:
        devices_for_type = sorted(metadata[selected_device_type].get("devices", []))
        locations_for_type = sorted(metadata[selected_device_type].get("locations", []))

    selected_device_id = st.sidebar.selectbox(
        "Device ID:",
        options=devices_for_type,
        key="ai_device_id_select",
        index=0 if devices_for_type else None,
        disabled=not devices_for_type
    )

    selected_location_id = st.sidebar.selectbox(
        "Location ID:",
        options=locations_for_type,
        key="ai_location_id_select",
        index=0 if locations_for_type else None,
        disabled=not locations_for_type
    )

    constructed_collection_name = None
    if selected_device_id and selected_location_id:
        collection_base = f"router_{selected_device_id}_{selected_location_id}"
        constructed_collection_name = f"{collection_base}_log_vector"
        st.sidebar.info(f"Selected Collection: `{constructed_collection_name}`")
    else:
        st.sidebar.warning("Please select a Device Type, Device ID, and Location ID.")

    st.sidebar.markdown("---")

    # --- Common Filters ---
    st.sidebar.subheader("🔍 Filters")
    st.sidebar.caption("Apply these filters to the AI Summary.")

    end_time_dt = datetime.now()
    time_options = {
        "Last 1 hour": timedelta(hours=1),
        "Last 6 hours": timedelta(hours=6),
        "Last 24 hours": timedelta(hours=24),
        "Last 3 days": timedelta(days=3),
        "Last 7 days": timedelta(days=7),
        "Custom": None
    }
    selected_time_range = st.sidebar.selectbox(
        "Select time range",
        list(time_options.keys()),
        index=2,
        key="ai_time_range"
    )

    start_time_dt = None
    end_time_dt_final = end_time_dt

    if selected_time_range == "Custom":
        scol1, scol2 = st.sidebar.columns(2)
        with scol1:
            start_date = st.date_input(
                "Start date",
                end_time_dt - timedelta(days=1),
                key="ai_start_d"
            )
            start_time_input = st.time_input(
                "Start time",
                datetime.strptime("00:00", "%H:%M").time(),
                key="ai_start_t"
            )
        with scol2:
            end_date = st.date_input(
                "End date",
                end_time_dt,
                key="ai_end_d"
            )
            end_time_input = st.time_input(
                "End time",
                datetime.strptime("23:59", "%H:%M").time(),
                key="ai_end_t"
            )

        start_time_dt = datetime.combine(start_date, start_time_input)
        end_time_dt_final = datetime.combine(end_date, end_time_input)

        if start_time_dt >= end_time_dt_final:
            st.sidebar.error("Start date/time must be before end date/time.")
            start_time_dt = None
    elif selected_time_range in time_options:
        start_time_dt = end_time_dt_final - time_options[selected_time_range]

    summary_start_time_unix = int(start_time_dt.timestamp()) if start_time_dt else None
    summary_end_time_unix = int(end_time_dt_final.timestamp()) if end_time_dt_final else None

    categories = ["All"]
    event_types = ["All"]
    interfaces = ["All"]
    if selected_device_type and selected_device_type in metadata:
        type_meta = metadata[selected_device_type]
        categories.extend(sorted(list(set(type_meta.get("categories", [])))))
        event_types.extend(sorted(list(set(type_meta.get("event_types", [])))))
        interfaces.extend(sorted(list(set(type_meta.get("interfaces", [])))))
        st.sidebar.caption(f"Filters available for type: `{selected_device_type}`")
    else:
        st.sidebar.caption("Select Device Type to see specific filters.")

    selected_category = st.sidebar.selectbox(
        "Category",
        categories,
        key="ai_cat"
    )
    selected_event_type = st.sidebar.selectbox(
        "Event Type",
        event_types,
        key="ai_evt"
    )
    severities = ["All", "0", "1", "2", "3", "4", "5", "6"]
    selected_severity = st.sidebar.selectbox(
        "Severity",
        severities,
        key="ai_sev"
    )
    selected_interface = st.sidebar.selectbox(
        "Interface",
        interfaces,
        key="ai_int"
    )

    st.session_state['ai_filters'] = {
        "start_time_dt": start_time_dt,
        "end_time_dt": end_time_dt_final,
        "start_time_unix": summary_start_time_unix,
        "end_time_unix": summary_end_time_unix,
        "category": selected_category if selected_category != "All" else None,
        "event_type": selected_event_type if selected_event_type != "All" else None,
        "severity": selected_severity if selected_severity != "All" else None,
        "interface": selected_interface if selected_interface != "All" else None
    }

    st.sidebar.markdown("---")

    # --- AI Summary Controls ---
    st.sidebar.subheader("🧠 AI Summary Options")
    # Use the API health status stored in session state
    api_is_healthy = st.session_state.get('api_healthy', False) # Default to False if not checked yet
    api_is_unhealthy = not api_is_healthy

    if api_is_unhealthy:
         st.sidebar.caption("⚠️ AI features unavailable (API offline).")
    else:
        st.sidebar.caption("Generate an AI summary of recent logs.")

    summary_limit_ai = st.sidebar.slider(
        "Max log samples for summary:",
        10, 100, 30, 5,
        key="ai_summary_limit",
        help="Maximum number of recent logs the AI should analyze for the summary.",
        disabled=api_is_unhealthy or not constructed_collection_name
    )

    include_latest_log = st.sidebar.checkbox(
        "Include Latest Log",
        value=False,
        key="ai_include_latest_log",
        help="Include the most recent log matching the filters in the summary.",
        disabled=api_is_unhealthy or not constructed_collection_name
    )

    gen_summary_disabled = api_is_unhealthy or not constructed_collection_name
    if st.sidebar.button("✨ Generate AI Summary", key="gen_ai_summary_btn", type="primary", disabled=gen_summary_disabled):
        # Set session state flag and parameters for summary generation
        st.session_state['generate_ai_summary_clicked'] = True
        st.session_state['summary_collection_name'] = constructed_collection_name
        st.session_state['summary_limit'] = st.session_state.get("ai_summary_limit", 30)
        st.session_state['include_latest_log'] = include_latest_log

    if st.sidebar.button("🔄 Reset Filters & Data"):
        keys_to_clear = [
            'ai_filters', 'ai_summary_result', 'ai_detailed_result',
            'last_requested_summary_limit'
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        # Also clear the API health status so it gets re-checked on next load
        if 'api_healthy' in st.session_state:
            del st.session_state['api_healthy']
        st.rerun()

    # System Info Section
    with st.sidebar:
        st.markdown("---")
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### 🖥️ System Info")
        
        # Check database connection for status display
        try:
            db_connected = health_check()
        except:
            db_connected = False
            
        st.markdown(f"""
        **Version:** 1.2.0
        
        **Database:** {'<span class="status-success">Connected ✅</span>' if db_connected else '<span class="status-error">Disconnected ❌</span>'}
        
        **Last Update:** {(datetime.now() - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M")}
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Quick Navigation Links
        st.markdown("---")
        st.markdown("### 🔗 Quick Links")
        
        st.page_link("pages/1_Network_Overview.py", label="🌍 Network Overview", icon="🌍")
        st.page_link("pages/2_Devices_Dashboard.py", label="📊 Devices Dashboard", icon="📊")
        st.page_link("pages/3_Interface_Monitoring.py", label="🔌 Interface Monitoring", icon="🔌")
        st.page_link("pages/4_Chatbot.py", label="🤖 AI Chatbot", icon="🤖")
        # Current page
        st.markdown("**🧠 AI Summary**")
        
        # Return to home - fixing the path error
        st.page_link("main.py", label="🏠 Return to Home", icon="🏠")
        
        # Logout option
        st.markdown("---")
        if st.button("🚪 Logout", type="primary"):
            logout()
            
        st.caption("© 2023 MIR Networks")

    return constructed_collection_name

# --- Main Content ---
def main():
    st.title("🧠 AI-Powered Log Analysis")
    st.markdown("Generate AI summaries of network logs or analyze specific logs by ID or custom input.")

    # Perform health check once and store in session state if not already done
    # This check will run when the page loads or after Reset
    if 'api_healthy' not in st.session_state:
        with st.spinner("Checking API status..."):
            st.session_state['api_healthy'] = health_check() # Call the function from Main.py
            logger.info(f"API Health Check Result: {st.session_state['api_healthy']}")

    # Render sidebar - this now uses the session state for disabling
    constructed_collection_name = render_sidebar()
    
    # Handle Generate AI Summary button click
    if st.session_state.get('generate_ai_summary_clicked', False):
        # Reset the flag
        st.session_state['generate_ai_summary_clicked'] = False
        
        # Get parameters from session state
        collection_name = st.session_state.get('summary_collection_name')
        summary_limit_val = st.session_state.get('summary_limit', 30)
        include_latest = st.session_state.get('include_latest_log', False)
        
        if collection_name:
            st.session_state['last_requested_summary_limit'] = summary_limit_val
            common_filters = st.session_state.get('ai_filters', {})
            payload = {
                "collection_name": collection_name,
                "limit": summary_limit_val,
                "start_time": common_filters.get("start_time_unix"),
                "end_time": common_filters.get("end_time_unix"),
                "include_latest": include_latest,
                "category": common_filters.get("category"),
                "event_type": common_filters.get("event_type"),
                "severity": common_filters.get("severity"),
                "interface": common_filters.get("interface")
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            logger.info(f"Payload for summary generation: {payload}")
            with st.spinner(f"Generating AI summary for '{collection_name}'..."):
                api_response = call_api("/generate_summary", payload)
                st.session_state['ai_summary_result'] = api_response
                st.session_state.pop('ai_detailed_result', None)
                st.success("Summary requested!")
        else:
            st.error("Cannot generate summary without a selected collection.")

    # Check API status from session state and display warning if needed
    api_ok = st.session_state.get('api_healthy', False)
    if not api_ok:
        st.warning("AI features are unavailable due to API connection issues. Please check the backend API service.", icon="⚠️")

    # Display AI Summary Results
    ai_summary_result = st.session_state.get('ai_summary_result')
    if ai_summary_result and isinstance(ai_summary_result, dict) and ai_summary_result.get('collection_name') == constructed_collection_name:
        st.markdown("---")
        st.markdown(f"#### AI Summary Result for `{ai_summary_result.get('collection_name')}`")
        requested_limit = st.session_state.get('last_requested_summary_limit')
        if requested_limit is not None:
            st.caption(f"Summary requested using a maximum of {requested_limit} log samples.")
        display_api_analysis(ai_summary_result)
    elif ai_summary_result and constructed_collection_name is not None:
        st.info(f"Previous summary for `{ai_summary_result.get('collection_name')}` hidden. Generate a new summary for `{constructed_collection_name}`.")
        # Removed the potentially distracting message here.

    # Detailed Analysis Section
    st.markdown("---")
    st.markdown("#### Analyze Specific Logs")
    if not constructed_collection_name:
        st.warning("⬅️ Select a Device Type, ID, and Location in the sidebar to enable detailed analysis.")
    else:
        st.markdown(f"Analyze specific logs using their IDs or by pasting raw log data (using context from `{constructed_collection_name}`).")
        # Disable analysis options if API is not healthy
        analysis_disabled = not api_ok

        analysis_method = st.radio(
            "Select analysis input method:",
            ["Analyze by Log IDs", "Analyze Custom Logs (JSON format)"],
            key="ai_analysis_method_radio",
            horizontal=True,
            disabled=analysis_disabled or not constructed_collection_name # Added analysis_disabled
        )

        if analysis_method == "Analyze by Log IDs":
            st.markdown("**Enter Log IDs (one per line):**")
            log_ids_input_ai = st.text_area(
                "Log IDs:", height=100, key="ai_log_ids_input",
                help="Provide the unique identifier for each log entry stored in Qdrant (usually a UUID string).",
                placeholder="e.g., a1b2c3d4-e5f6-7890-1234-567890abcdef\n...",
                disabled=analysis_disabled or not constructed_collection_name # Added analysis_disabled
            )
            log_ids_ai = [log_id.strip() for log_id in log_ids_input_ai.split("\n") if log_id.strip()]
            analyze_ids_disabled = not log_ids_ai or not constructed_collection_name or analysis_disabled # Added analysis_disabled
            if st.button("🔬 Analyze Specific Log IDs", key="analyze_ai_ids_btn", disabled=analyze_ids_disabled):
                if constructed_collection_name and log_ids_ai:
                    with st.spinner(f"Analyzing {len(log_ids_ai)} log(s) from '{constructed_collection_name}'..."):
                        payload = {"log_ids": log_ids_ai, "logs": [], "collection_name": constructed_collection_name}
                        api_response = call_api("/analyze_logs", payload)
                        st.session_state['ai_detailed_result'] = api_response
                        st.session_state.pop('ai_summary_result', None)
                        st.session_state.pop('last_requested_summary_limit', None)
                elif not log_ids_ai:
                    st.warning("Please enter at least one Log ID.")
                elif not constructed_collection_name:
                     st.warning("Please select a collection first.")


        elif analysis_method == "Analyze Custom Logs (JSON format)":
            st.markdown("**Paste logs as a JSON list of objects:**")
            custom_logs_input_ai = st.text_area(
                "Custom Logs (JSON list):", height=200, key="ai_custom_logs_input",
                help='Input must be a valid JSON list `[...]` where each element is a JSON object `{...}` representing a log entry.',
                placeholder='[{"timestamp": 1678886400, "raw_log": "Log message 1", "severity": 5}, \n {"timestamp": 1678886405, "message": "Log message 2", "device": "fw-abc"}]',
                disabled=analysis_disabled or not constructed_collection_name # Added analysis_disabled
            )
            analyze_custom_disabled = not custom_logs_input_ai.strip() or not constructed_collection_name or analysis_disabled # Added analysis_disabled
            if st.button("🔬 Analyze Custom Logs", key="analyze_ai_custom_btn", disabled=analyze_custom_disabled):
                if constructed_collection_name and custom_logs_input_ai.strip():
                    custom_logs_list = None
                    is_valid_json = False
                    try:
                        parsed_input = json.loads(custom_logs_input_ai)
                        if isinstance(parsed_input, list):
                            if all(isinstance(item, dict) for item in parsed_input):
                                custom_logs_list = parsed_input
                                is_valid_json = True
                            else:
                                st.warning("Invalid JSON: All elements in the list must be objects (dictionaries).")
                        else:
                            st.warning("Invalid JSON: Input must be a list of log objects.")
                    except json.JSONDecodeError as json_e:
                        st.warning(f"Invalid JSON format: {str(json_e)}")
                        logger.error(f"JSON decode error in custom logs input: {json_e}")

                    if is_valid_json and custom_logs_list:
                        with st.spinner(f"Analyzing {len(custom_logs_list)} custom log(s) for '{constructed_collection_name}'..."):
                            payload = {"log_ids": [], "logs": custom_logs_list, "collection_name": constructed_collection_name}
                            api_response = call_api("/analyze_logs", payload)
                            st.session_state['ai_detailed_result'] = api_response
                            st.session_state.pop('ai_summary_result', None)
                            st.session_state.pop('last_requested_summary_limit', None)
                    elif not custom_logs_input_ai.strip():
                        st.warning("Please paste custom logs in JSON format.")
                    elif not constructed_collection_name:
                         st.warning("Please select a collection first.")


    # Display Detailed Analysis Results
    ai_detailed_result = st.session_state.get('ai_detailed_result')
    if ai_detailed_result and isinstance(ai_detailed_result, dict) and ai_detailed_result.get('collection_name') == constructed_collection_name:
        st.markdown("---")
        st.markdown(f"#### Detailed Analysis Result for `{ai_detailed_result.get('collection_name')}`")
        display_api_analysis(ai_detailed_result)
    elif ai_detailed_result and constructed_collection_name is not None:
        st.info(f"Detailed analysis result for previous collection (`{ai_detailed_result.get('collection_name')}`) hidden. Analyze again for `{constructed_collection_name}`.")


if __name__ == "__main__":
    main()
# END OF FILE 5_ai_summary.py