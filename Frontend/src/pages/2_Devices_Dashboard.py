# src/pages/Dashboard.py
"""
Network Monitoring Dashboard - Devices Dashboard Component.
Adapted from the existing main.py file to work in a multipage application.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from loguru import logger

# Import utilities
from src.utils.qdrant_client import get_qdrant_client, load_metadata, get_collections, fetch_data
from src.utils.data_processing import detect_flapping_interfaces, analyze_interface_stability
from src.utils.visualization import create_interface_timeline, create_interface_heatmap
from src.utils.auth import check_auth 

# Configure page
st.set_page_config(
    page_title="2_Devices_Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- Authentication Check ---
check_auth()
logger.info(f"User '{st.session_state.username}' accessed Devices Dashboard page.")

# Page title
st.title("📊 Devices Dashboard")
st.markdown("Overview of network health, events, and activity.")

# Global variables
CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))
metadata = load_metadata()

# Sidebar controls
def render_sidebar_controls():
    st.sidebar.header("Device Controls")
    
    # Time range selection
    st.sidebar.subheader("Time Range")
    end_time = datetime.now()
    time_options = {
        "Last 1 hour": timedelta(hours=1),
        "Last 6 hours": timedelta(hours=6),
        "Last 24 hours": timedelta(hours=24),
        "Last 3 days": timedelta(days=3),
        "Last 7 days": timedelta(days=7),
        "Custom": None
    }
    
    selected_time = st.sidebar.selectbox("Select time range", list(time_options.keys()))
    
    if selected_time == "Custom":
        start_date = st.sidebar.date_input("Start date", end_time - timedelta(days=1))
        start_time_input = st.sidebar.time_input("Start time", datetime.strptime("00:00", "%H:%M").time())
        end_date = st.sidebar.date_input("End date", end_time)
        end_time_input = st.sidebar.time_input("End time", datetime.strptime("23:59", "%H:%M").time())
        
        start_time = datetime.combine(start_date, start_time_input)
        end_time = datetime.combine(end_date, end_time_input)
    else:
        start_time = end_time - time_options[selected_time]
    
    # Device selection
    st.sidebar.subheader("Device Filters")
    
    # Get all device types
    device_types = [k for k in metadata.keys() if k != "collections"]
    selected_device_type = st.sidebar.selectbox("Device Type", device_types)
    
    # Get devices of selected type
    devices = metadata[selected_device_type]["devices"] if selected_device_type in metadata else []
    selected_device = st.sidebar.selectbox("Device", ["All"] + devices)
    
    # Get locations for selected device type
    locations = metadata[selected_device_type]["locations"] if selected_device_type in metadata else []
    selected_location = st.sidebar.selectbox("Location", ["All"] + locations)
    
    # Determine the appropriate collection
    if selected_device != "All" and selected_location != "All":
        collection_name = f"router_{selected_device}_{selected_location}_log_vector"
    else:
        # Default to first available collection
        collections = get_collections()
        collection_name = collections[0] if collections else None
    
    # Event filters
    st.sidebar.subheader("Event Filters")
    
    # Category selection
    categories = metadata[selected_device_type]["categories"] if selected_device_type in metadata else []
    selected_category = st.sidebar.selectbox("Category", ["All"] + categories)
    
    # Event type selection
    event_types = metadata[selected_device_type]["event_types"] if selected_device_type in metadata else []
    if selected_category != "All":
        # Filter event types by category prefix
        filtered_event_types = [et for et in event_types if et.startswith(selected_category)]
        selected_event_type = st.sidebar.selectbox("Event Type", ["All"] + filtered_event_types)
    else:
        selected_event_type = st.sidebar.selectbox("Event Type", ["All"] + event_types)
    
    # Severity selection
    severities = ["0", "1", "2", "3", "4", "5", "6"]
    selected_severity = st.sidebar.selectbox("Severity", ["All"] + severities)
    
    # Interface selection
    if selected_device_type in metadata and "interfaces" in metadata[selected_device_type] and metadata[selected_device_type]["interfaces"]:
        interfaces = metadata[selected_device_type]["interfaces"]
        selected_interface = st.sidebar.selectbox("Interface", ["All"] + interfaces)
    else:
        selected_interface = "All"
    
    # Return all selected filters
    return {
        "start_time": start_time,
        "end_time": end_time,
        "device_type": selected_device_type,
        "device": selected_device if selected_device != "All" else None,
        "location": selected_location if selected_location != "All" else None,
        "category": selected_category if selected_category != "All" else None,
        "event_type": selected_event_type if selected_event_type != "All" else None,
        "severity": selected_severity if selected_severity != "All" else None,
        "interface": selected_interface if selected_interface != "All" else None,
        "collection_name": collection_name
    }

# Main dashboard layout
def main():
    # Render sidebar and get filters
    filters = render_sidebar_controls()
    
    # Fetch data button
    if st.sidebar.button("Fetch Data"):
        with st.spinner("Fetching data..."):
            # Fetch data
            df = fetch_data(
                collection_name=filters["collection_name"],
                start_time=filters["start_time"],
                end_time=filters["end_time"],
                limit=5000,
                device=filters["device"],
                location=filters["location"],
                category=filters["category"],
                event_type=filters["event_type"],
                severity=filters["severity"],
                interface=filters["interface"]
            )
            
            if df.empty:
                st.warning("No data found matching the specified filters.")
                return
            
            # Store the dataframe in session state
            st.session_state['data'] = df
            st.session_state['collection_name'] = filters["collection_name"]
    
    # Reset filters button
    if st.sidebar.button("Reset Filters"):
        # Clear session state
        if 'data' in st.session_state:
            del st.session_state['data']
        if 'collection_name' in st.session_state:
            del st.session_state['collection_name']
    
    # Basic text search in sidebar
    st.sidebar.subheader("Text Search")
    search_query = st.sidebar.text_input("Search Query (keywords)")
    search_k = st.sidebar.slider("Top K Results", 5, 50, 10)
    
    if st.sidebar.button("Search") and search_query and 'collection_name' in st.session_state:
        # Code for search functionality (simplified)
        st.info(f"Searching for '{search_query}' is not implemented in this version.")
    
    # Check if data is available in session state
    if 'data' in st.session_state and not st.session_state['data'].empty:
        df = st.session_state['data']
        
        # Create tabs for different dashboard sections
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Network Devices Overview",
            "Time-based Analysis",
            "Event Analysis",
            "Interface Status",
            "Log Explorer"
        ])
        
        with tab1:
            # Display network metrics in top row
            st.subheader("📊 Network Health Metrics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_events = len(df)
                st.metric("Total Events", f"{total_events:,}")
            
            with col2:
                unique_devices = df['device'].nunique()
                st.metric("Active Devices", unique_devices)
            
            with col3:
                # Count interface down events
                down_events = df[df['event_type'].str.contains('IF_DOWN', na=False)].shape[0] if 'event_type' in df.columns else 0
                st.metric("Interface Down Events", down_events)
            
            with col4:
                # Use utility function to detect flapping interfaces
                flapping_df = detect_flapping_interfaces(df)
                flapping_count = len(flapping_df)
                st.metric("Flapping Interfaces", flapping_count)
            
            # Event Timeline
            st.subheader("📈 Event Timeline")
            
            if 'timestamp_dt' in df.columns:
                # Group by timestamp (hourly) and count events
                df['hour'] = df['timestamp_dt'].dt.floor('h')
                events_by_hour = df.groupby('hour').size().reset_index(name='count')
                
                # Create timeline chart
                fig = px.line(
                    events_by_hour, 
                    x='hour', 
                    y='count',
                    title="Event Frequency Over Time",
                    labels={'hour': 'Time', 'count': 'Number of Events'}
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            # Category Distribution
            st.subheader("📊 Event Category Distribution")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if 'category' in df.columns:
                    # Create category distribution chart
                    category_counts = df['category'].value_counts().reset_index()
                    category_counts.columns = ['category', 'count']
                    
                    fig = px.pie(
                        category_counts,
                        values='count',
                        names='category',
                        title="Event Categories",
                        hole=0.4
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if 'severity' in df.columns:
                    # Create severity distribution chart
                    severity_counts = df['severity'].value_counts().reset_index()
                    severity_counts.columns = ['severity', 'count']
                    
                    # Map severity levels to descriptions
                    severity_map = {
                        '0': '0 - Emergency',
                        '1': '1 - Alert',
                        '2': '2 - Critical',
                        '3': '3 - Error',
                        '4': '4 - Warning',
                        '5': '5 - Notice',
                        '6': '6 - Info'
                    }
                    
                    severity_counts['severity_label'] = severity_counts['severity'].map(
                        lambda x: severity_map.get(str(x), f"{x} - Unknown")
                    )
                    
                    fig = px.bar(
                        severity_counts,
                        x='severity_label',
                        y='count',
                        title="Event Severity Distribution",
                        labels={'severity_label': 'Severity Level', 'count': 'Number of Events'},
                        color='severity_label',
                        color_discrete_sequence=px.colors.sequential.Plasma_r
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.subheader("📊 Time-based Analysis")
            
            if 'timestamp_dt' in df.columns:
                # Create interface heatmap using utility function
                heatmap_fig = create_interface_heatmap(df)
                st.plotly_chart(heatmap_fig, use_container_width=True)
        
        with tab3:
            st.subheader("🔍 Event Analysis")
            
            # Event type distribution
            if 'event_type' in df.columns:
                # Get top event types
                top_events_df = df['event_type'].value_counts().reset_index()
                top_events_df.columns = ['event_type', 'count']
                top_events_df = top_events_df.head(15)  # Top 15 event types
                
                fig = px.bar(
                    top_events_df,
                    x='event_type',
                    y='count',
                    title="Top Event Types",
                    labels={'event_type': 'Event Type', 'count': 'Number of Events'}
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
                
                # If we have timestamp data, show top events over time
                if 'timestamp_dt' in df.columns and 'hour' in df.columns:
                    # Get top 5 event types
                    top_5_events = top_events_df.head(5)['event_type'].tolist()
                    
                    # Filter dataframe to include only top event types
                    df_top_events = df[df['event_type'].isin(top_5_events)]
                    
                    # Group by hour and event type
                    events_by_hour_type = df_top_events.groupby(['hour', 'event_type']).size().reset_index(name='count')
                    
                    # Create stacked area chart
                    fig = px.area(
                        events_by_hour_type,
                        x='hour',
                        y='count',
                        color='event_type',
                        title="Top Event Types Over Time",
                        labels={'hour': 'Time', 'count': 'Number of Events', 'event_type': 'Event Type'}
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            
            # Location-based analysis
            if 'location' in df.columns:
                st.subheader("📍 Location-based Analysis")
                
                location_counts = df['location'].value_counts().reset_index()
                location_counts.columns = ['location', 'count']
                
                fig = px.bar(
                    location_counts,
                    x='location',
                    y='count',
                    title="Events by Location",
                    labels={'location': 'Location', 'count': 'Number of Events'}
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # If we have category data, show event categories by location
                if 'category' in df.columns:
                    # Group by location and category
                    location_category = df.groupby(['location', 'category']).size().reset_index(name='count')
                    
                    fig = px.bar(
                        location_category,
                        x='location',
                        y='count',
                        color='category',
                        title="Event Categories by Location",
                        labels={'location': 'Location', 'count': 'Number of Events', 'category': 'Category'}
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
        
        with tab4:
            # Interface Status Analysis
            st.subheader("🔌 Interface Status Analysis")
            
            st.markdown("""
            For detailed interface monitoring, including flapping detection and stability analysis, 
            please visit the [Interface Monitoring](Interface_Monitoring) page.
            """)
            
            # Show a preview of interface data
            if 'interface' in df.columns:
                interface_df = df[df['interface'].notna()]
                if not interface_df.empty:
                    # Use utility function to analyze interface stability
                    stability_df = analyze_interface_stability(interface_df)
                    
                    # Show stability metrics
                    if not stability_df.empty:
                        st.subheader("Interface Stability Overview")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            unstable_count = len(stability_df[stability_df['stability_score'] < 50])
                            st.metric("Unstable Interfaces", unstable_count)
                        
                        with col2:
                            avg_stability = stability_df['stability_score'].mean()
                            st.metric("Average Stability Score", f"{avg_stability:.1f}")
                        
                        with col3:
                            high_freq = len(stability_df[stability_df['event_frequency'] > 10])
                            st.metric("High Event Frequency", high_freq)
                    
                    # Show interface timeline using utility function
                    st.subheader("Interface Event Timeline (Preview)")
                    timeline_fig = create_interface_timeline(df.head(100))
                    st.plotly_chart(timeline_fig, use_container_width=True)
        
        with tab5:
            st.subheader("📜 Log Explorer")
            
            # Display the most recent events
            if 'timestamp_dt' in df.columns:
                # Add search functionality
                search_term = st.text_input("Filter logs by keyword")
                
                # Filter dataframe if search term is provided
                if search_term:
                    filtered_df = df[df.apply(lambda row: any(search_term.lower() in str(val).lower() for val in row), axis=1)]
                else:
                    filtered_df = df
                
                # Sort by timestamp
                recent_df = filtered_df.sort_values('timestamp_dt', ascending=False).head(50)
                
                # Format the dataframe for display
                if 'raw_log' in recent_df.columns:
                    display_cols = ['timestamp_dt', 'device', 'location', 'category', 'event_type', 'severity', 'raw_log']
                else:
                    display_cols = [col for col in ['timestamp_dt', 'device', 'location', 'category', 'event_type', 'severity', 'message'] 
                                   if col in recent_df.columns]
                
                st.dataframe(recent_df[display_cols], use_container_width=True)
                
                # Add export functionality
                if st.button("Export to CSV"):
                    csv = recent_df[display_cols].to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"network_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            else:
                st.dataframe(df.head(50), use_container_width=True)
    else:
        st.info("👈 Select filters and click 'Fetch Data' to begin exploring network events.")

if __name__ == "__main__":
    main()