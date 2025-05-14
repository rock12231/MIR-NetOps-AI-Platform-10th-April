# src/pages/3_Interface_Monitoring.py
"""
Interface Monitoring Component for Network Monitoring Dashboard.

This component provides specialized analysis of network interface status,
including flapping detection, stability scoring, and event timeline analysis.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from loguru import logger
import requests
import os
import json

# Updated imports for src directory structure
# Removed: from src.utils.qdrant_client import load_metadata, health_check
from src.utils.data_processing import (
    detect_flapping_interfaces, 
    analyze_interface_stability,
    categorize_interface_events,
    get_interface_timeline,
    calculate_interface_metrics
)
from src.utils.visualization import (
    create_interface_timeline,
    create_flapping_interfaces_chart,
    create_stability_chart,
    create_event_distribution_chart,
    create_interface_heatmap,
    create_interface_metrics_cards
)
from src.utils.auth import check_auth, init_session_state, logout  # Added logout for sidebar

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

# Backend API URL
BACKEND_URL = "http://backend-api:8001" # Correct endpoint for backend API

# Configure page
st.set_page_config(
    page_title="3_Interface_Monitoring",
    page_icon="🔌",
    layout="wide"
)


# --- Authentication Check ---
init_session_state()  # Initialize session state
check_auth()
logger.info(f"User '{st.session_state.username}' accessed Interface Monitoring page.")

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

# Configure logging
logger.info("Loading Interface Monitoring Component")

# Global variables
metadata = None

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
        logger.info(f"Calling API: {url} with params: {params}")
        response = requests.get(url, params=params)
        logger.info(f"API Response Status: {response.status_code}")
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        data = response.json()
        logger.info(f"API Response Data: {data}")
        return data
    except requests.RequestException as e:
        st.error(f"API Error: {str(e)}")
        logger.error(f"API Error ({endpoint}): {str(e)}")
        return None

# Function to add explanatory tooltips
def add_tooltip(text, tooltip):
    return f"{text} ℹ️" if tooltip else text

# Sidebar controls for interface monitoring
def render_sidebar_controls():
    global metadata
    
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
    
    st.sidebar.header("🔌 Interface Monitoring Controls")
    
    # Time range selection
    st.sidebar.subheader("⏱️ Time Range")
    end_time = datetime.now()
    time_options = {
        "Last 6 hours": timedelta(hours=6),
        "Last 24 hours": timedelta(hours=24),
        "Last 3 days": timedelta(days=3),
        "Last 7 days": timedelta(days=7),
        "Last 30 days": timedelta(days=30),  # Adding a longer option
        "Custom": None
    }
    
    selected_time = st.sidebar.selectbox("Select time range", list(time_options.keys()))
    
    if selected_time == "Custom":
        start_date = st.sidebar.date_input("📅 Start date", end_time - timedelta(days=1))
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
    
    # Device filter options (focused on AGW devices with interface data)
    st.sidebar.subheader("🔧 Device Filters")
    
    # Get devices that typically have interface data (AGW)
    if "agw" in metadata and "devices" in metadata["agw"]:
        agw_devices = metadata["agw"]["devices"]
        selected_device = st.sidebar.selectbox(
            "Device", 
            ["All"] + agw_devices,
            help="Select a specific device to analyze or 'All' for all devices"
        )
    else:
        selected_device = "All"
        agw_devices = []
    
    # Get locations for AGW devices
    if "agw" in metadata and "locations" in metadata["agw"]:
        agw_locations = metadata["agw"]["locations"]
        selected_location = st.sidebar.selectbox(
            "Location", 
            ["All"] + agw_locations,
            help="Select a specific location to analyze or 'All' for all locations"
        )
    else:
        selected_location = "All"
        agw_locations = []
    
    # Interface selection
    if "agw" in metadata and "interfaces" in metadata["agw"]:
        interfaces = metadata["agw"]["interfaces"]
        selected_interface = st.sidebar.selectbox(
            "Interface", 
            ["All"] + interfaces,
            help="Select a specific interface to analyze or 'All' for all interfaces"
        )
    else:
        selected_interface = "All"
        interfaces = []
    
    # Analysis parameters
    st.sidebar.subheader("⚙️ Analysis Parameters")
    
    # Flapping detection parameters
    time_threshold = st.sidebar.slider(
        "Flapping Time Threshold (minutes)", 
        min_value=5, 
        max_value=120, 
        value=30,
        help="Maximum time between state changes to be considered flapping"
    )
    
    min_transitions = st.sidebar.slider(
        "Minimum Transitions for Flapping", 
        min_value=2, 
        max_value=10, 
        value=3,
        help="Minimum number of state transitions required to classify as flapping"
    )
    
    # Stability analysis window
    stability_window = st.sidebar.selectbox(
        "Stability Analysis Window",
        ["6 hours", "12 hours", "24 hours", "48 hours", "7 days"],
        index=2,
        help="Time window for calculating interface stability metrics"
    )
    
    # Map selected window to hours
    stability_window_hours = {
        "6 hours": 6,
        "12 hours": 12,
        "24 hours": 24,
        "48 hours": 48,
        "7 days": 168
    }[stability_window]
    
    # Action buttons
    if st.sidebar.button("📊 Load Interface Data", type="primary"):
        # Don't use 'pass' here as it would disconnect the button from the functionality
        # The actual functionality will be handled in the main function
        st.session_state["load_interface_data_clicked"] = True

    if st.sidebar.button("🔄 Reset Filters"):
        # Don't use 'pass' here as it would disconnect the button from the functionality
        st.session_state["reset_filters_clicked"] = True
    
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
        
        # Logout option
        st.markdown("---")
        if st.button("🚪 Logout", type="primary"):
            logout()
            
        st.caption("© 2023 MIR Networks")
    
    # Return all selected filters
    return {
        "start_time": start_time,
        "end_time": end_time,
        "device": selected_device if selected_device != "All" else None,
        "location": selected_location if selected_location != "All" else None,
        "interface": selected_interface if selected_interface != "All" else None,
        "time_threshold": time_threshold,
        "min_transitions": min_transitions,
        "stability_window_hours": stability_window_hours,
        "all_devices": agw_devices,
        "all_locations": agw_locations,
        "all_interfaces": interfaces
    }

# Function to load interface data from API
def load_interface_data_from_api(filters):
    """
    Load interface data based on selected filters using the API.
    
    Args:
        filters (dict): Dictionary of filter parameters
        
    Returns:
        pandas.DataFrame: DataFrame with filtered interface data
    """
    with st.spinner("Loading interface data..."):
        try:
            # Prepare API call parameters
            params = {
                "start_time": filters["start_time"].isoformat(),
                "end_time": filters["end_time"].isoformat(),
                "total_limit": 10000  # Higher limit for comprehensive analysis
            }
            
            # Add optional filters if specified
            if filters["device"]:
                params["device"] = filters["device"]
            if filters["location"]:
                params["location"] = filters["location"]
            if filters["interface"]:
                params["interface"] = filters["interface"]
            
            # Make API call to get interface data
            response = call_api("/api/v1/interfaces/interface_data", params)
            
            if not response:
                logger.warning("No interface data found with the specified filters")
                return None
                
            if "data" not in response or not response["data"]:
                logger.warning("No interface data found with the specified filters")
                return None
                
            # Convert to DataFrame
            df = pd.DataFrame(response["data"])
            
            # Convert timestamp to datetime if present
            if 'timestamp' in df.columns:
                df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='s')
            
            # Categorize events for better analysis
            # We could call the categorize_events API, but it's faster to do it locally
            df = categorize_interface_events(df)
            logger.info(f"Loaded {len(df)} interface events")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading interface data: {str(e)}")
            st.error(f"Error loading data: {str(e)}")
            return None

# Main function
def main():
    # Page title
    st.title("🔌 Interface Monitoring")
    st.markdown("Focused analysis of network interface status, stability, and flapping issues.")
    
    # Get filters from sidebar
    filters = render_sidebar_controls()
    
    # Handle the Load Interface Data button click using session state
    if st.session_state.get("load_interface_data_clicked", False):
        # Reset the flag
        st.session_state["load_interface_data_clicked"] = False
        
        # Show spinner during loading
        with st.spinner("Loading and processing interface data..."):
            # Load data and store in session state
            df = load_interface_data_from_api(filters)
            
            if df is not None and not df.empty:
                st.session_state["interface_data"] = df
                st.session_state["interface_filters"] = filters
                st.success(f"Loaded {len(df)} interface events from {filters['start_time']} to {filters['end_time']}")
            else:
                st.warning("No interface data found with the selected filters.")
                if "interface_data" in st.session_state:
                    del st.session_state["interface_data"]
    
    # Handle Reset Filters button click
    if st.session_state.get("reset_filters_clicked", False):
        # Reset the flag
        st.session_state["reset_filters_clicked"] = False
        
        # Clear session state data
        if "interface_data" in st.session_state:
            del st.session_state["interface_data"]
        if "interface_filters" in st.session_state:
            del st.session_state["interface_filters"]
        
        # Rerun the app to reset the UI
        st.rerun()
    
    # Check if we have data to analyze
    if "interface_data" in st.session_state and not st.session_state["interface_data"].empty:
        df = st.session_state["interface_data"]
        current_filters = st.session_state["interface_filters"]
        
        # Add explanatory info section about metrics
        st.info("""
        **Understanding Interface Metrics:**
        - **Interfaces Down**: Interfaces currently in a non-operational state
        - **Flapping Interfaces**: Interfaces rapidly changing between up/down states
        - **Stability Score**: A composite measure (0-100) based on event frequency, down events ratio, and configuration changes
        - **Note**: An interface can be down without flapping, flapping but currently up, or stable but intentionally down
        """)
        
        # Calculate interface metrics
        with st.spinner("Calculating interface metrics..."):
            # Option 1: Calculate metrics using the API
            params = {
                "start_time": current_filters["start_time"].isoformat(),
                "end_time": current_filters["end_time"].isoformat(),
                "time_window_hours": int(current_filters["stability_window_hours"])  # Ensure it's an int
            }
            
            # Add optional filters if specified
            if current_filters["device"]:
                params["device"] = str(current_filters["device"])  # Ensure it's a string
            if current_filters["location"]:
                params["location"] = str(current_filters["location"])  # Ensure it's a string
            
            # Call API to get metrics
            logger.info(f"Calling interface_metrics API with params: {params}")
            metrics_response = call_api("/api/v1/interfaces/interface_metrics", params)
            
            if metrics_response:
                # Check if the response has the expected format
                required_metrics = ['total_interfaces', 'down_interfaces', 'flapping_interfaces', 'status_changes']
                if all(metric in metrics_response for metric in required_metrics):
                    metrics = metrics_response
                else:
                    # Response is missing some required metrics
                    logger.warning(f"API response missing required metrics: {metrics_response}")
                    metrics = {
                        'total_interfaces': metrics_response.get('total_interfaces', 0),
                        'down_interfaces': metrics_response.get('down_interfaces', 0),
                        'flapping_interfaces': metrics_response.get('flapping_interfaces', 0),
                        'status_changes': metrics_response.get('status_changes', 0),
                        'config_changes': metrics_response.get('config_changes', 0)
                    }
            else:
                # No valid response, create default metrics
                logger.warning("No metrics response from API, using default values")
                metrics = {
                    'total_interfaces': 0,
                    'down_interfaces': 0,
                    'flapping_interfaces': 0,
                    'status_changes': 0,
                    'config_changes': 0
                }
                
                # Try to calculate locally if we have data
                if 'df' in locals() and df is not None and not df.empty:
                    try:
                        local_metrics = calculate_interface_metrics(df, current_filters["stability_window_hours"])
                        metrics.update(local_metrics)
                    except Exception as e:
                        logger.error(f"Error calculating local metrics: {str(e)}")
            
            # Display debug info 
            st.sidebar.markdown("### Debug Info")
            if st.sidebar.checkbox("Show API Response", value=False):
                st.sidebar.json(metrics_response)
                
            if st.sidebar.checkbox("Show Processed Metrics", value=False):
                st.sidebar.json(metrics)
            
            # Add test preset option
            if st.sidebar.checkbox("Enable Test Data", value=False):
                st.sidebar.info("Using test data instead of API values")
                metrics = {
                    'total_interfaces': 24,
                    'down_interfaces': 3,
                    'flapping_interfaces': 2,
                    'status_changes': 47,
                    'config_changes': 8
                }
        
        # Display metrics cards with tooltips
        st.subheader("Interface Health Dashboard")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                add_tooltip("Monitored Interfaces", "Total number of interfaces being tracked"), 
                metrics['total_interfaces']
            )
            
        with col2:
            st.metric(
                add_tooltip("Interfaces Down", "Interfaces currently in a non-operational state"), 
                metrics['down_interfaces']
            )
            
        with col3:
            st.metric(
                add_tooltip("Flapping Interfaces", "Interfaces with rapid state transitions within the configured time threshold"), 
                metrics['flapping_interfaces']
            )
            
        with col4:
            st.metric(
                add_tooltip("Total Status Changes", "Total count of interface state transitions (up/down events)"), 
                metrics['status_changes']
            )
        
        # Add interface health visualization
        col1, col2 = st.columns(2)
        
        with col1:
            # Create a gauge chart for interface health
            if metrics['total_interfaces'] > 0:
                # First count interfaces that are both down and flapping
                down_and_flapping = min(metrics['down_interfaces'], metrics['flapping_interfaces'])
                
                # Calculate unique problematic interfaces
                problematic_interfaces = (metrics['down_interfaces'] + 
                                        metrics['flapping_interfaces'] - 
                                        down_and_flapping)  # Subtract overlapping interfaces
                
                health_pct = 100 * (metrics['total_interfaces'] - problematic_interfaces) / metrics['total_interfaces']
                health_pct = max(0, min(100, health_pct))  # Ensure health is between 0 and 100
            else:
                health_pct = 100
                
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=health_pct,
                title={'text': "Interface Health"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "darkgreen"},
                    'steps': [
                        {'range': [0, 50], 'color': "red"},
                        {'range': [50, 75], 'color': "orange"},
                        {'range': [75, 100], 'color': "lightgreen"}
                    ],
                    'threshold': {
                        'line': {'color': "black", 'width': 4},
                        'thickness': 0.75,
                        'value': health_pct
                    }
                }
            ))
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True, key="health_gauge")
        
        with col2:
            # Create a donut chart showing status distribution
            # Calculate overlapping states
            down_and_flapping = min(metrics['down_interfaces'], metrics['flapping_interfaces'])
            only_down = metrics['down_interfaces'] - down_and_flapping
            only_flapping = metrics['flapping_interfaces'] - down_and_flapping
            stable = metrics['total_interfaces'] - only_down - only_flapping - down_and_flapping
            
            labels = ["Up & Stable", "Down Only", "Flapping Only", "Down & Flapping"]
            values = [stable, only_down, only_flapping, down_and_flapping]
            colors = ['green', 'red', 'orange', 'purple']
            
            # Filter out zero values
            non_zero_indices = [i for i, v in enumerate(values) if v > 0]
            labels = [labels[i] for i in non_zero_indices]
            values = [values[i] for i in non_zero_indices]
            colors = [colors[i] for i in non_zero_indices]
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=.4,
                marker_colors=colors
            )])
            fig.update_layout(
                title_text="Interface Status Distribution",
                height=250
            )
            st.plotly_chart(fig, use_container_width=True, key="status_donut")
        
        # Create tabs for different analysis views
        tab1, tab2, tab3, tab4 = st.tabs([
            "Event Timeline", 
            "Flapping Interfaces", 
            "Interface Stability", 
            "Detailed Analysis"
        ])
        
        with tab1:
            st.subheader("⏱️ Interface Event Timeline")
            st.markdown("""
            Visualizes interface events over time to identify patterns, correlations, and potential issues.
            """)
            
            # Get specific interface for timeline if selected
            selected_interface_timeline = st.selectbox(
                "Select Interface for Timeline",
                ["All Interfaces"] + sorted(df["interface"].unique().tolist())
            )
            
            # Filter data for selected interface
            if selected_interface_timeline != "All Interfaces":
                timeline_df = df[df["interface"] == selected_interface_timeline]
                st.info(f"Showing timeline for interface {selected_interface_timeline}")
            else:
                # For "All Interfaces", limit to avoid overcrowding
                if df.shape[0] > 500:
                    st.info(f"Showing a sample of events for all interfaces")
                    # Use stratified sampling to get representative events from each interface
                    sampled_df = pd.DataFrame()
                    for interface, group in df.groupby('interface'):
                        sample_size = min(50, len(group))  # Up to 50 events per interface
                        sampled_df = pd.concat([sampled_df, group.sample(sample_size)])
                    timeline_df = sampled_df
                else:
                    timeline_df = df
            
            # Create timeline visualization
            with st.spinner("Creating interface timeline..."):
                timeline_chart = create_interface_timeline(timeline_df)
                st.plotly_chart(timeline_chart, use_container_width=True, key="timeline_chart")
            
            # Create heatmap of interface activity
            st.subheader("Interface Activity Heatmap")
            
            # Only show heatmap if we have enough data
            if len(df) > 20:
                with st.spinner("Creating interface heatmap..."):
                    heatmap = create_interface_heatmap(df)
                    st.plotly_chart(heatmap, use_container_width=True, key="interface_heatmap")
            else:
                st.info("Not enough data to generate interface activity heatmap.")
        
        with tab2:
            st.subheader("🔄 Flapping Interface Analysis")
            st.markdown("""
            Identifies interfaces that are rapidly changing state (flapping). These interfaces may indicate 
            hardware issues, connectivity problems, or configuration errors.
            """)
            
            # Detect flapping interfaces using API
            with st.spinner("Detecting flapping interfaces..."):
                # Prepare API call parameters
                params = {
                    "start_time": current_filters["start_time"].isoformat(),
                    "end_time": current_filters["end_time"].isoformat(),
                    "time_threshold_minutes": current_filters["time_threshold"],
                    "min_transitions": current_filters["min_transitions"]
                }
                
                # Add optional filters if specified
                if current_filters["device"]:
                    params["device"] = current_filters["device"]
                if current_filters["location"]:
                    params["location"] = current_filters["location"]
                if current_filters["interface"]:
                    params["interface"] = current_filters["interface"]
                
                # Call API to detect flapping interfaces
                flapping_response = call_api("/api/v1/interfaces/detect_flapping", params)
                
                if flapping_response and "data" in flapping_response:
                    flapping_interfaces = flapping_response["data"]
                    flapping_df = pd.DataFrame(flapping_interfaces) if flapping_interfaces else pd.DataFrame()
                else:
                    # Fallback to local calculation
                    flapping_df = detect_flapping_interfaces(
                        df, 
                        time_threshold_minutes=current_filters["time_threshold"],
                        min_transitions=current_filters["min_transitions"]
                    )
            
            if not flapping_df.empty:
                # Show flapping interfaces chart
                flapping_chart = create_flapping_interfaces_chart(flapping_df)
                st.plotly_chart(flapping_chart, use_container_width=True, key="flapping_chart")
                
                # Format dataframe for display
                display_df = flapping_df[['device', 'location', 'interface', 
                                       'transitions_count', 'total_duration_minutes',
                                       'first_event', 'last_event']]
                display_df = display_df.rename(columns={
                    'transitions_count': 'State Changes',
                    'total_duration_minutes': 'Duration (min)',
                    'first_event': 'First Event',
                    'last_event': 'Last Event'
                })
                if 'Duration (min)' in display_df.columns:
                    if isinstance(display_df['Duration (min)'].iloc[0], float):
                        display_df['Duration (min)'] = display_df['Duration (min)'].round(2)
                
                # Display table
                st.subheader("Flapping Interfaces Details")
                st.dataframe(display_df, use_container_width=True)
                
                # Warning message about flapping interfaces
                st.warning(f"Detected {len(flapping_df)} flapping interfaces! These may require attention.")
                
                # Recommendations
                st.subheader("Recommendations")
                st.markdown("""
                * Check physical connections for these interfaces
                * Verify interface configurations (speed/duplex settings)
                * Monitor connected devices for power or hardware issues
                * Consider using the `shutdown`/`no shutdown` commands to reset these interfaces
                """)
            else:
                st.success("No flapping interfaces detected with current parameters.")
                
                # Show parameters used
                st.info(f"""
                **Flapping Detection Parameters:**
                * Time Threshold: {current_filters['time_threshold']} minutes
                * Minimum Transitions: {current_filters['min_transitions']} state changes
                
                Try adjusting these parameters in the sidebar if you suspect interface flapping.
                """)
        
        with tab3:
            st.subheader("📊 Interface Stability Analysis")
            st.markdown("""
            Analyzes the stability of network interfaces based on event frequency, down events ratio,
            and configuration changes. Lower stability scores indicate potentially problematic interfaces.
            """)
            
            # Calculate stability metrics using API
            with st.spinner("Analyzing interface stability..."):
                # Prepare API call parameters
                params = {
                    "start_time": current_filters["start_time"].isoformat(),
                    "end_time": current_filters["end_time"].isoformat(),
                    "time_window_hours": current_filters["stability_window_hours"]
                }
                
                # Add optional filters if specified
                if current_filters["device"]:
                    params["device"] = current_filters["device"]
                if current_filters["location"]:
                    params["location"] = current_filters["location"]
                if current_filters["interface"]:
                    params["interface"] = current_filters["interface"]
                
                # Call API to analyze interface stability
                stability_response = call_api("/api/v1/interfaces/analyze_stability", params)
                
                if stability_response and "data" in stability_response:
                    stability_metrics = stability_response["data"]
                    stability_df = pd.DataFrame(stability_metrics) if stability_metrics else pd.DataFrame()
                else:
                    # Fallback to local calculation
                    stability_df = analyze_interface_stability(df, current_filters["stability_window_hours"])
            
            if not stability_df.empty:
                # Show stability scores chart
                stability_chart = create_stability_chart(stability_df)
                st.plotly_chart(stability_chart, use_container_width=True, key="stability_chart")
                
                # Display detailed stability metrics
                st.subheader("Interface Stability Details")
                
                # Format for display
                display_df = stability_df[['device', 'location', 'interface', 
                                        'stability_score', 'total_events', 
                                        'up_events', 'down_events', 'event_frequency']]
                display_df = display_df.rename(columns={
                    'stability_score': 'Stability Score',
                    'total_events': 'Total Events',
                    'up_events': 'Up Events',
                    'down_events': 'Down Events',
                    'event_frequency': 'Events/Hour'
                })
                
                if 'Events/Hour' in display_df.columns:
                    if isinstance(display_df['Events/Hour'].iloc[0], float):
                        display_df['Events/Hour'] = display_df['Events/Hour'].round(2)
                
                if 'Stability Score' in display_df.columns:
                    if isinstance(display_df['Stability Score'].iloc[0], float):
                        display_df['Stability Score'] = display_df['Stability Score'].round(1)
                
                # Sort by stability score (ascending)
                display_df = display_df.sort_values('Stability Score')
                
                st.dataframe(display_df, use_container_width=True)
                
                # Explanation of stability score
                with st.expander("How is the Stability Score calculated?"):
                    st.info("""
                    **Stability Score Calculation:**
                    The stability score (0-100) is calculated using the following formula:
                    
                    ```
                    stability_score = 100 - (
                        40 * down_ratio + 
                        40 * min(1, event_frequency/5) + 
                        20 * min(1, config_changes/5)
                    )
                    ```
                    
                    Where:
                    * **Down events ratio (40%)**: Ratio of down events to total events
                    * **Event frequency (40%)**: Number of events per hour (capped at 5 events/hour)
                    * **Configuration changes (20%)**: Number of configuration changes (capped at 5 changes)
                    
                    **Interpretation:**
                    * Higher scores (closer to 100) indicate more stable interfaces
                    * Lower scores indicate potentially problematic interfaces
                    * Scores below 50 typically indicate interfaces requiring attention
                    * Scores below 30 indicate critical issues that should be investigated immediately
                    """)
                
                # Event distribution chart
                st.subheader("Event Type Distribution")
                distribution_chart = create_event_distribution_chart(df)
                st.plotly_chart(distribution_chart, use_container_width=True, key="distribution_chart")
            else:
                st.info("Insufficient data for stability analysis.")
        
        with tab4:
            st.subheader("🔍 Detailed Interface Analysis")
            
            # Let user select a specific interface to analyze in detail
            interfaces_list = sorted(df["interface"].unique().tolist())
            if interfaces_list:
                selected_detail_interface = st.selectbox(
                    "Select Interface for Detailed Analysis",
                    interfaces_list
                )
                
                # Filter data for selected interface
                interface_data = df[df["interface"] == selected_detail_interface]
                
                if not interface_data.empty:
                    # Display interface info
                    st.subheader(f"Interface: {selected_detail_interface}")
                    
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Events", len(interface_data))
                        
                    with col2:
                        up_events = interface_data[interface_data['event_type'].str.contains('IF_UP', na=False)].shape[0]
                        st.metric("Up Events", up_events)
                        
                    with col3:
                        down_events = interface_data[interface_data['event_type'].str.contains('IF_DOWN', na=False)].shape[0]
                        st.metric("Down Events", down_events)
                        
                    with col4:
                        config_events = interface_data[
                            interface_data['event_type'].str.contains('DUPLEX|SPEED|FLOW_CONTROL|BANDWIDTH', na=False)
                        ].shape[0]
                        st.metric("Config Changes", config_events)
                    
                    # Get flapping status
                    with st.spinner("Analyzing flapping status..."):
                        # Prepare API call parameters for flapping detection
                        params = {
                            "start_time": current_filters["start_time"].isoformat(),
                            "end_time": current_filters["end_time"].isoformat(),
                            "interface": selected_detail_interface,
                            "time_threshold_minutes": current_filters["time_threshold"],
                            "min_transitions": current_filters["min_transitions"]
                        }
                        
                        # Add optional filters if specified
                        if current_filters["device"]:
                            params["device"] = current_filters["device"]
                        if current_filters["location"]:
                            params["location"] = current_filters["location"]
                        
                        # Call API to detect flapping
                        flapping_response = call_api("/api/v1/interfaces/detect_flapping", params)
                        
                        if flapping_response and "data" in flapping_response:
                            is_flapping = len(flapping_response["data"]) > 0
                        else:
                            # Fallback to local detection
                            flapping_df = detect_flapping_interfaces(
                                interface_data, 
                                time_threshold_minutes=current_filters["time_threshold"],
                                min_transitions=current_filters["min_transitions"]
                            )
                            is_flapping = not flapping_df.empty
                    
                    # Get stability metrics for this interface
                    with st.spinner("Calculating stability metrics..."):
                        # Prepare API call parameters for stability analysis
                        params = {
                            "start_time": current_filters["start_time"].isoformat(),
                            "end_time": current_filters["end_time"].isoformat(),
                            "interface": selected_detail_interface,
                            "time_window_hours": current_filters["stability_window_hours"]
                        }
                        
                        # Add optional filters if specified
                        if current_filters["device"]:
                            params["device"] = current_filters["device"]
                        if current_filters["location"]:
                            params["location"] = current_filters["location"]
                        
                        # Call API to analyze stability
                        stability_response = call_api("/api/v1/interfaces/analyze_stability", params)
                        
                        if stability_response and "data" in stability_response and stability_response["data"]:
                            stability_df = pd.DataFrame(stability_response["data"])
                            stability_score = stability_df['stability_score'].iloc[0] if not stability_df.empty else None
                        else:
                            # Fallback to local calculation
                            stability_df = analyze_interface_stability(interface_data, current_filters["stability_window_hours"])
                            stability_score = stability_df['stability_score'].iloc[0] if not stability_df.empty else None
                    
                    # Interface status
                    status = "Stable"
                    if is_flapping:
                        status = "⚠️ FLAPPING"
                    elif stability_score is not None and stability_score < 50:
                        status = "⚠️ UNSTABLE"
                    elif down_events > 0:
                        # Check if last event was a down event
                        last_event = interface_data.sort_values('timestamp_dt', ascending=False).iloc[0]
                        if 'IF_DOWN' in str(last_event['event_type']):
                            status = "⚠️ DOWN"
                    
                    st.info(f"**Current Status**: {status}")
                    
                    if stability_score is not None:
                        st.progress(min(100, int(stability_score)) / 100, text=f"Stability Score: {stability_score:.1f}/100")
                    
                    # Timeline for this interface
                    st.subheader("Event Timeline")
                    timeline_chart = create_interface_timeline(interface_data)
                    st.plotly_chart(timeline_chart, use_container_width=True, key=f"timeline_{selected_detail_interface}")
                    
                    # Show raw events
                    st.subheader("Event Log")
                    interface_data_sorted = interface_data.sort_values('timestamp_dt', ascending=False)
                    
                    # Determine columns for display
                    if 'raw_log' in interface_data_sorted.columns:
                        display_cols = ['timestamp_dt', 'event_type', 'event_category', 'raw_log']
                    else:
                        display_cols = [col for col in ['timestamp_dt', 'event_type', 'event_category', 'message'] 
                                      if col in interface_data_sorted.columns]
                    
                    # Add option to show full raw logs
                    show_full_logs = st.checkbox("Show full raw logs", value=False)
                    
                    # Display events with pagination
                    page_size = 25  # Number of events per page
                    total_pages = (len(interface_data_sorted) + page_size - 1) // page_size
                    
                    if total_pages > 1:
                        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
                        start_idx = (page - 1) * page_size
                        end_idx = min(start_idx + page_size, len(interface_data_sorted))
                        st.info(f"Showing events {start_idx+1}-{end_idx} of {len(interface_data_sorted)}")
                        paginated_data = interface_data_sorted.iloc[start_idx:end_idx]
                    else:
                        paginated_data = interface_data_sorted
                    
                    if show_full_logs:
                        st.dataframe(paginated_data[display_cols], use_container_width=True)
                    else:
                        # Truncate raw logs for better display
                        if 'raw_log' in display_cols:
                            truncated_data = paginated_data.copy()
                            truncated_data['raw_log'] = truncated_data['raw_log'].str.slice(0, 100) + '...'
                            st.dataframe(truncated_data[display_cols], use_container_width=True)
                        else:
                            st.dataframe(paginated_data[display_cols], use_container_width=True)
                    
                    # Add export functionality
                    if st.button("Export to CSV"):
                        csv = interface_data_sorted[display_cols].to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"{selected_detail_interface}_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.warning(f"No events found for interface {selected_detail_interface}")
            else:
                st.warning("No interface data available for detailed analysis")
    else:
        # Show instructions when no data is loaded
        st.info("👈 Use the sidebar to select filters and click 'Load Interface Data' to begin interface analysis.")
        
        # Information about the dashboard without image (more robust)
        st.markdown("""
        ## Interface Monitoring Dashboard
        
        This dashboard provides specialized tools for monitoring and analyzing network interfaces:
        
        ### 🔄 Flapping Interface Detection
        Identifies interfaces that frequently change state within configurable time thresholds.
        
        ### 📊 Interface Stability Scoring
        Calculates stability metrics for each interface using event frequency, down events ratio, and configuration changes.
        
        ### ⏱️ Event Timeline Analysis
        Time-based visualization of interface events to identify patterns and correlations.
        
        ### 🔍 Detailed Interface Diagnostics
        In-depth analysis of individual interface history, event logs, and state transitions.
        """)

if __name__ == "__main__":
    main()