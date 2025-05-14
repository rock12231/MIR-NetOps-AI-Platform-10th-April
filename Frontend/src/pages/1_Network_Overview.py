# src/pages/1_Network_Overview.py
"""
Network Overview Page - High-level insights across the entire network infrastructure.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from loguru import logger
import requests
import json
import os

# Import utilities
# Removed: from src.utils.qdrant_client import load_metadata, health_check
from src.utils.data_processing import categorize_interface_events, calculate_network_health, analyze_device_distribution, create_location_health_matrix
from src.utils.visualization import COLOR_SCALES, create_network_topology_map, create_event_trend_chart, create_location_heatmap
from src.utils.auth import check_auth, init_session_state, logout

# Backend API URL
BACKEND_URL = "http://backend-api:8001"  # Update this with your actual backend URL

# --- Added new metadata loading code ---
METADATA_PATH = os.getenv('METADATA_PATH', 'data/qdrant_db_metadata.json')
CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))

@st.cache_data(ttl=CACHE_TTL)
def load_metadata():
    """
    Load metadata about collections with error handling.
    
    Returns:
        dict: Metadata dictionary with collections and device information
    """
    try:
        if os.path.exists(METADATA_PATH):
            with open(METADATA_PATH, 'r') as f:
                metadata = json.load(f)
                # Validate metadata structure
                required_keys = ["collections", "agw", "dgw", "fw", "vadc"]
                if not all(key in metadata for key in required_keys):
                    logger.error("Invalid metadata structure. Missing required keys.")
                    return get_default_metadata()
                return metadata
        else:
            logger.warning(f"Metadata file {METADATA_PATH} not found. Using default configuration.")
            return get_default_metadata()
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing metadata file: {str(e)}")
        return get_default_metadata()
    except Exception as e:
        logger.error(f"Error loading metadata: {str(e)}")
        return get_default_metadata()

def get_default_metadata():
    """
    Return default metadata structure.
    
    Returns:
        dict: Default metadata
    """
    return {
        "collections": [],
        "agw": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": []},
        "dgw": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": []},
        "fw": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": [], "processes": []},
        "vadc": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": []}
    }

# --- Authentication Check ---
init_session_state()  # Initialize session state
check_auth()
logger.info(f"User '{st.session_state.username}' accessed the Network Overview page.")

# Configure page
st.set_page_config(
    page_title="1_Network_Overview",
    page_icon="🌍",
    layout="wide"
)

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

# Function to render sidebar controls
def render_sidebar_controls():
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
    
    # Network Overview Controls - keep existing controls
    st.sidebar.header("🌐 Network Overview Controls")
    
    # Time range selection
    st.sidebar.subheader("⏱️ Time Range")
    end_time = datetime.now()
    time_options = {
        "Last 24 hours": timedelta(hours=24),
        "Last 3 days": timedelta(days=3),
        "Last 7 days": timedelta(days=7),
        "Last 30 days": timedelta(days=30),
        "Custom": None
    }
    
    selected_time = st.sidebar.selectbox("Select time range", list(time_options.keys()))
    
    if selected_time == "Custom":
        start_date = st.sidebar.date_input("📅 Start date", end_time - timedelta(days=7))
        start_time_input = st.sidebar.time_input("🕒 Start time", datetime.strptime("00:00", "%H:%M").time())
        end_date = st.sidebar.date_input("📅 End date", end_time)
        end_time_input = st.sidebar.time_input("🕒 End time", datetime.strptime("23:59", "%H:%M").time())
        
        start_time = datetime.combine(start_date, start_time_input)
        end_time = datetime.combine(end_date, end_time_input)
    else:
        start_time = end_time - time_options[selected_time]
    
    # Load metadata with spinner and success message
    with st.sidebar:
        with st.spinner("Loading metadata..."):
            metadata = load_metadata()
            st.success("Metadata loaded successfully!")
    
    # Device type selection
    st.sidebar.subheader("🔧 Device Filters")
    device_types = [k for k in metadata.keys() if k != "collections"]
    selected_device_types = st.sidebar.multiselect(
        "Device Types", 
        options=device_types,
        default=device_types
    )
    
    # Location selection
    locations = []
    for device_type in selected_device_types:
        if device_type in metadata and "locations" in metadata[device_type]:
            locations.extend(metadata[device_type]["locations"])
    locations = sorted(list(set(locations)))
    
    selected_locations = st.sidebar.multiselect(
        "📍 Locations",
        options=locations,
        default=[]
    )
    
    # Add Reset Filters button
    if st.sidebar.button("🔄 Reset Filters"):
        # Set session state flag to trigger reset in main function
        st.session_state["reset_filters_clicked"] = True

    # Add Load Data button
    if st.sidebar.button("📊 Load Network Data", type="primary"):
        # Set session state flag to trigger load in main function  
        st.session_state["load_network_data_clicked"] = True

    # System Info Section - Update to remove health check
    with st.sidebar:
        st.markdown("---")
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### 🖥️ System Info")
            
        st.markdown(f"""
        **Version:** 1.2.0
        
        **Last Update:** {(datetime.now() - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M")}
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Logout option
        st.markdown("---")
        if st.button("🚪 Logout", type="primary"):
            logout()
            
        st.caption("© 2023 MIR Networks")
    
    return {
        "start_time": start_time,
        "end_time": end_time,
        "device_types": selected_device_types,
        "locations": selected_locations if selected_locations else None
    }

# Function to call backend API
def call_api(endpoint, params=None):
    """
    Call the backend API and handle errors.
    
    Args:
        endpoint (str): API endpoint path (without base URL)
        params (dict, optional): Query parameters
        
    Returns:
        dict or None: API response or None on error
    """
    try:
        url = f"{BACKEND_URL}{endpoint}"
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        return response.json()
    except requests.RequestException as e:
        st.error(f"API Error: {str(e)}")
        logger.error(f"API Error ({endpoint}): {str(e)}")
        return None

# Function to fetch aggregated network data from API
def fetch_aggregated_network_data_from_api(start_time, end_time, device_types=None, locations=None):
    """
    Fetch aggregated network data from the backend API.
    
    Args:
        start_time (datetime): Start time for filtering
        end_time (datetime): End time for filtering
        device_types (list, optional): List of device types to include
        locations (list, optional): List of locations to include
        
    Returns:
        pandas.DataFrame: DataFrame with network data
    """
    # Prepare parameters
    params = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    
    # Add device types if specified
    if device_types:
        params["device_types"] = device_types
        
    # Add locations if specified
    if locations:
        params["locations"] = locations
    
    # Make API call
    response = call_api("/api/v1/network/aggregated_data", params)
    
    # Process response
    if response and "data" in response:
        df = pd.DataFrame(response["data"])
        
        # Ensure 'timestamp_dt' column exists
        if 'timestamp' in df.columns:
            df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='s')
            
        logger.info(f"Loaded {len(df)} records from API")
        return df
    else:
        logger.warning("No data returned from API")
        return pd.DataFrame()

# Page title
st.title("🌍 Network Overview")
st.markdown("High-level insights across the entire network infrastructure.")

def main():
    # Get filters from sidebar
    filters = render_sidebar_controls()
    
    # Handle Reset Filters button click
    if st.session_state.get("reset_filters_clicked", False):
        # Reset the flag
        st.session_state["reset_filters_clicked"] = False
        
        # Clear session state data
        st.session_state.pop("network_data", None)
        st.session_state.pop("network_filters", None)
        
        # Rerun to reset UI
        st.rerun()
    
    # Handle Load Network Data button click
    if st.session_state.get("load_network_data_clicked", False):
        # Reset the flag
        st.session_state["load_network_data_clicked"] = False
        
        with st.spinner("Loading network data..."):
            try:
                # Fetch aggregated data from API
                network_data = fetch_aggregated_network_data_from_api(
                    start_time=filters["start_time"],
                    end_time=filters["end_time"],
                    device_types=filters["device_types"],
                    locations=filters["locations"]
                )
                
                if not network_data.empty:
                    # Store in session state
                    st.session_state["network_data"] = network_data
                    st.session_state["network_filters"] = filters
                    st.success(f"Loaded {len(network_data)} events from {filters['start_time']} to {filters['end_time']}")
                else:
                    st.warning("No data found with the selected filters.")
                    if "network_data" in st.session_state:
                        del st.session_state["network_data"]
            except Exception as e:
                st.error(f"Error loading data: {str(e)}")
    
    # Check if data is available
    if "network_data" in st.session_state:
        network_data = st.session_state["network_data"]
        
        # Network Topology and Health Section
        st.subheader("Network Topology and Health")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Network map
            st.markdown("#### Network Topology Map")
            network_map = create_network_topology_map(network_data)
            st.plotly_chart(network_map, use_container_width=True)
        
        with col2:
            # Device type distribution
            st.markdown("#### Total Syslog Activity Distribution")
            
            # Calculate device distribution
            distribution = analyze_device_distribution(network_data)
            
            # Create pie chart for device types
            if not distribution["by_type"].empty:
                fig = px.pie(
                    distribution["by_type"], 
                    values='count', 
                    names='device_type',
                    title="Total Syslog Activity Distribution",
                    color='device_type',
                    color_discrete_map={
                        'agw': '#5046e4',
                        'dgw': '#ff6b6b',
                        'fw': '#51cf66',
                        'vadc': '#fab005'
                    },
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No device distribution data available.")
        
        # Global Performance Metrics Section
        st.subheader("Global Performance Metrics")
        
        # Calculate metrics
        health_score = calculate_network_health(network_data)
        active_devices = network_data['device'].nunique()
        critical_events = len(network_data[network_data['severity'].isin(['0', '1', '2'])])
        problem_locations = network_data[network_data['severity'].isin(['0', '1', '2'])]['location'].nunique()
        
        # Display metrics in cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Network Health", f"{health_score:.1f}%")
        
        with col2:
            st.metric("Active Devices", active_devices)
        
        with col3:
            st.metric("Critical Events", critical_events)
        
        with col4:
            st.metric("Problem Locations", problem_locations)
        
        # Event trend chart
        event_trend = create_event_trend_chart(network_data)
        st.plotly_chart(event_trend, use_container_width=True)
        
        # Location Health Summary Section
        st.subheader("Location Health Summary")
        
        # Create location health matrix
        health_matrix = create_location_health_matrix(network_data)
        
        if not health_matrix.empty:
            # Create heatmap
            heatmap = create_location_heatmap(health_matrix)
            st.plotly_chart(heatmap, use_container_width=True)
        else:
            st.info("Insufficient data for location health analysis.")
        
    else:
        # Show instructions
        st.info("👈 Use the sidebar to select filters and click 'Load Network Data' to begin exploring network-wide insights.")
        
        # Placeholder description of the page
        st.markdown("""
        ## Network Overview Dashboard
        
        This dashboard provides high-level insights across your entire network infrastructure:
        
        ### 🌐 Network Topology and Device Distribution
        - Interactive visualization of network topology
        - Breakdown of devices by type and location
        
        ### 📊 Global Performance Metrics
        - Network-wide health score
        - Critical event monitoring
        - Event trends over time
        
        ### 🗺️ Location Health Summary
        - Health metrics by location
        - Time-based analysis of network activity
        - Identification of problem areas
        """)

if __name__ == "__main__":
    main()