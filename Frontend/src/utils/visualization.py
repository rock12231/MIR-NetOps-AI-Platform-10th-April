# src/utils/visualization.py
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import numpy as np


# Color schemes
COLOR_SCALES = {
    'status': {
        'Status Up': '#00CC96',      # Green
        'Status Down': '#EF553B',    # Red
        'Link Failure': '#AB63FA',   # Purple
        'Admin Down': '#FFA15A',     # Orange
        'Config Change': '#19D3F3',  # Light Blue
        'Other': '#636EFA'           # Blue
    },
    'severity': px.colors.sequential.Plasma_r,
    'stability': px.colors.diverging.RdYlGn,
    'flapping': px.colors.sequential.Reds
}


def create_interface_timeline(df, height=400, max_interfaces=20):
    """
    Create a timeline visualization of interface events.
    
    Args:
        df (pandas.DataFrame): DataFrame with interface events
        height (int): Height of the chart
        max_interfaces (int): Maximum number of interfaces to display
        
    Returns:
        plotly.graph_objects.Figure: Timeline figure
    """
    if df.empty or 'timestamp_dt' not in df.columns or 'interface' not in df.columns:
        return go.Figure()
    
    # Create a copy of the DataFrame to avoid modifying the original
    plot_df = df.copy()
    
    # If too many interfaces, limit to most active ones
    if plot_df['interface'].nunique() > max_interfaces:
        top_interfaces = plot_df.groupby('interface').size().nlargest(max_interfaces).index
        plot_df = plot_df[plot_df['interface'].isin(top_interfaces)]
        st.info(f"Showing timeline for the {max_interfaces} most active interfaces out of {df['interface'].nunique()} total interfaces.")
    
    # Map event types to colors
    if 'event_category' not in plot_df.columns:
        plot_df.loc[:, 'event_category'] = 'Other'
    
    # Create hover text
    plot_df.loc[:, 'hover_text'] = plot_df.apply(
        lambda row: f"Interface: {row['interface']}<br>" +
                   f"Event: {row['event_type']}<br>" +
                   f"Time: {row['timestamp_dt']}<br>" +
                   f"Device: {row['device']}" +
                   (f"<br>Raw: {row['raw_log']}" if 'raw_log' in plot_df.columns else ""),
        axis=1
    )
    
    # Create the figure
    fig = px.scatter(
        plot_df,
        x='timestamp_dt',
        y='interface',
        color='event_category',
        color_discrete_map=COLOR_SCALES['status'],
        hover_name='event_type',
        hover_data=['timestamp_dt', 'device'],
        custom_data=['hover_text'],
        title="Interface Event Timeline",
        labels={
            'timestamp_dt': 'Time',
            'interface': 'Interface',
            'event_category': 'Event Type'
        },
        height=height
    )
    
    # Improve hover information
    fig.update_traces(
        hovertemplate="%{customdata[0]}<extra></extra>"
    )
    
    # Improve layout
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Interface",
        legend_title="Event Type",
        hovermode="closest"
    )
    
    return fig


def create_flapping_interfaces_chart(df, height=400):
    """
    Create a bar chart of flapping interfaces.
    
    Args:
        df (pandas.DataFrame): DataFrame with flapping interface data
        height (int): Height of the chart
        
    Returns:
        plotly.graph_objects.Figure: Bar chart figure
    """
    if df.empty or 'interface' not in df.columns or 'transitions_count' not in df.columns:
        return go.Figure()
    
    # Sort by number of transitions
    df_sorted = df.sort_values('transitions_count', ascending=False)
    
    # Create the figure
    fig = px.bar(
        df_sorted,
        x='interface',
        y='transitions_count',
        color='transitions_count',
        color_continuous_scale=COLOR_SCALES['flapping'],
        title="Interface Flapping - State Transitions",
        labels={
            'interface': 'Interface',
            'transitions_count': 'Number of State Changes'
        },
        height=height
    )
    
    # Improve hover information
    fig.update_traces(
        hovertemplate="Interface: %{x}<br>State Changes: %{y}<br><extra></extra>"
    )
    
    # Improve layout
    fig.update_layout(
        xaxis_title="Interface",
        yaxis_title="Number of State Changes",
        coloraxis_showscale=True,
        coloraxis_colorbar=dict(
            title="Transitions"
        )
    )
    
    return fig


def create_stability_chart(df, height=400, max_interfaces=15):
    """
    Create a horizontal bar chart of interface stability scores.
    
    Args:
        df (pandas.DataFrame): DataFrame with interface stability data
        height (int): Height of the chart
        max_interfaces (int): Maximum number of interfaces to display
        
    Returns:
        plotly.graph_objects.Figure: Bar chart figure
    """
    if df.empty or 'interface' not in df.columns or 'stability_score' not in df.columns:
        return go.Figure()
    
    # Sort by stability score (ascending for worst first)
    df_sorted = df.sort_values('stability_score')
    
    # Limit to top N worst interfaces
    if len(df_sorted) > max_interfaces:
        df_display = df_sorted.head(max_interfaces)
        st.info(f"Showing the {max_interfaces} interfaces with lowest stability scores out of {len(df_sorted)} total interfaces.")
    else:
        df_display = df_sorted
    
    # Create the figure
    fig = px.bar(
        df_display,
        y='interface',
        x='stability_score',
        color='stability_score',
        color_continuous_scale=COLOR_SCALES['stability'],
        title="Interface Stability Scores",
        labels={
            'interface': 'Interface',
            'stability_score': 'Stability Score (0-100)'
        },
        height=height
    )
    
    # Add hover data
    fig.update_traces(
        hovertemplate="Interface: %{y}<br>Stability Score: %{x:.1f}<br><extra></extra>"
    )
    
    # Improve layout
    fig.update_layout(
        xaxis_title="Stability Score (higher is better)",
        yaxis_title="Interface",
        coloraxis_showscale=True,
        coloraxis_colorbar=dict(
            title="Stability"
        )
    )
    
    return fig


def create_event_distribution_chart(df, height=400):
    """
    Create a pie chart showing distribution of interface event types.
    
    Args:
        df (pandas.DataFrame): DataFrame with interface events
        height (int): Height of the chart
        
    Returns:
        plotly.graph_objects.Figure: Pie chart figure
    """
    if df.empty or 'event_type' not in df.columns:
        return go.Figure()
    
    # Count event types
    event_counts = df['event_type'].value_counts().reset_index()
    event_counts.columns = ['event_type', 'count']
    
    # Create the figure
    fig = px.pie(
        event_counts,
        values='count',
        names='event_type',
        title="Interface Event Type Distribution",
        height=height
    )
    
    # Improve layout
    fig.update_layout(
        legend_title="Event Type"
    )
    
    return fig


def create_interface_heatmap(df, height=500, max_interfaces=25):
    """
    Create a heatmap of interface activity over time.
    
    Args:
        df (pandas.DataFrame): DataFrame with interface events
        height (int): Height of the chart
        max_interfaces (int): Maximum number of interfaces to display
        
    Returns:
        plotly.graph_objects.Figure: Heatmap figure
    """
    if df.empty or 'timestamp_dt' not in df.columns or 'interface' not in df.columns:
        return go.Figure()
    
    # Create a copy of the DataFrame to avoid modifying the original
    plot_df = df.copy()
    
    # Extract hour from timestamp
    plot_df.loc[:, 'hour'] = plot_df['timestamp_dt'].dt.hour
    plot_df.loc[:, 'date'] = plot_df['timestamp_dt'].dt.date
    
    # Limit number of interfaces to avoid performance issues
    if plot_df['interface'].nunique() > max_interfaces:
        # Keep only the most active interfaces
        top_interfaces = plot_df.groupby('interface').size().nlargest(max_interfaces).index
        plot_df = plot_df[plot_df['interface'].isin(top_interfaces)]
        st.info(f"Showing heatmap for the {max_interfaces} most active interfaces out of {df['interface'].nunique()} total interfaces.")
    
    # Count events per interface and hour
    heatmap_data = plot_df.groupby(['interface', 'hour']).size().reset_index(name='count')
    
    # Pivot data for heatmap
    pivot_data = heatmap_data.pivot(index='interface', columns='hour', values='count')
    pivot_data = pivot_data.fillna(0)
    
    # Create the figure
    fig = px.imshow(
        pivot_data,
        labels=dict(x="Hour of Day", y="Interface", color="Event Count"),
        x=pivot_data.columns,
        y=pivot_data.index,
        color_continuous_scale="Viridis",
        title="Interface Activity by Hour of Day",
        height=height
    )
    
    # Improve hover information
    fig.update_traces(
        hovertemplate="Interface: %{y}<br>Hour: %{x}<br>Events: %{z}<extra></extra>"
    )
    
    # Improve layout
    fig.update_layout(
        xaxis_title="Hour of Day",
        yaxis_title="Interface",
        coloraxis_colorbar=dict(
            title="Event Count"
        )
    )
    
    return fig


def create_interface_metrics_cards(metrics):
    """
    Create a row of metric cards for interface dashboard.
    
    Args:
        metrics (dict): Dictionary of interface metrics
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Monitored Interfaces", metrics['total_interfaces'])
        
    with col2:
        st.metric("Interfaces Down", metrics['down_interfaces'])
        
    with col3:
        st.metric("Flapping Interfaces", metrics['flapping_interfaces'])
        
    with col4:
        st.metric("Total Status Changes", metrics['status_changes'])
        
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
        st.plotly_chart(fig, use_container_width=True)
    
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
        st.plotly_chart(fig, use_container_width=True)

def create_network_topology_map(device_data, height=400):
    """
    Create an interactive network topology visualization.
    
    Args:
        device_data (pandas.DataFrame): DataFrame with device distribution data
        height (int): Height of the chart
        
    Returns:
        plotly.graph_objects.Figure: Network map figure
    """
    if device_data.empty:
        return go.Figure()
    
    # Extract location data
    locations = device_data.groupby(['location']).size().reset_index(name='device_count')
    
    # Calculate health score by location
    health_by_location = device_data.groupby('location').apply(
        lambda x: 100 - min(100, x['severity'].astype(int).mean() * 20)
    ).reset_index(name='health_score')
    
    # Merge health score with location data
    locations = pd.merge(locations, health_by_location, on='location', how='left')
    locations['health_score'] = locations['health_score'].fillna(100)
    
    # Create color mapping based on health score
    def get_color(health):
        if health >= 90:
            return 'green'
        elif health >= 70:
            return 'lightgreen'
        elif health >= 50:
            return 'orange'
        else:
            return 'red'
    
    locations['color'] = locations['health_score'].apply(get_color)
    
    # Create node positions (in a circular layout)
    num_locations = len(locations)
    import math
    radius = 150
    center_x, center_y = 250, 200
    
    # Calculate positions
    angles = [2 * math.pi * i / num_locations for i in range(num_locations)]
    x_pos = [center_x + radius * math.cos(angle) for angle in angles]
    y_pos = [center_y + radius * math.sin(angle) for angle in angles]
    
    locations['x'] = x_pos
    locations['y'] = y_pos
    
    # Create figure
    fig = go.Figure()
    
    # Add center node
    fig.add_trace(go.Scatter(
        x=[center_x],
        y=[center_y],
        mode='markers+text',
        marker=dict(size=40, color='blue'),
        text=['Core'],
        textposition='middle center',
        textfont=dict(color='white'),
        hoverinfo='text',
        hovertext=['Network Core']
    ))
    
    # Add locations
    fig.add_trace(go.Scatter(
        x=locations['x'],
        y=locations['y'],
        mode='markers+text',
        marker=dict(
            size=30,
            color=locations['color'],
            line=dict(width=2, color='white')
        ),
        text=locations['location'],
        textposition='middle center',
        customdata=locations[['device_count', 'health_score']],
        hovertemplate='<b>%{text}</b><br>Devices: %{customdata[0]}<br>Health: %{customdata[1]:.1f}%',
    ))
    
    # Add connections to core
    for i, row in locations.iterrows():
        fig.add_trace(go.Scatter(
            x=[center_x, row['x']],
            y=[center_y, row['y']],
            mode='lines',
            line=dict(width=1, color='gray'),
            hoverinfo='none'
        ))
    
    # Update layout
    fig.update_layout(
        showlegend=False,
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor='white',
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False)
    )
    
    return fig

def create_event_trend_chart(df, height=400):
    """
    Create a time-series chart of events with severity breakdown.
    
    Args:
        df (pandas.DataFrame): DataFrame with network events
        height (int): Height of the chart
        
    Returns:
        plotly.graph_objects.Figure: Time-series chart figure
    """
    if df.empty or 'timestamp_dt' not in df.columns:
        return go.Figure()
    
    # Create hourly bins
    df['hour'] = df['timestamp_dt'].dt.floor('h')
    
    # Count all events
    all_events = df.groupby('hour').size().reset_index(name='count')
    
    # Count critical events (severity 0-2)
    critical_df = df[df['severity'].isin(['0', '1', '2'])]
    if not critical_df.empty:
        critical_events = critical_df.groupby('hour').size().reset_index(name='count')
    else:
        critical_events = pd.DataFrame(columns=['hour', 'count'])
        critical_events['count'] = 0
    
    # Create figure
    fig = go.Figure()
    
    # Add all events line
    fig.add_trace(go.Scatter(
        x=all_events['hour'],
        y=all_events['count'],
        mode='lines',
        name='All Events',
        line=dict(color='#5046e4', width=3)
    ))
    
    # Add critical events line
    fig.add_trace(go.Scatter(
        x=critical_events['hour'],
        y=critical_events['count'],
        mode='lines',
        name='Critical Events',
        line=dict(color='#ff6b6b', width=3)
    ))
    
    # Update layout
    fig.update_layout(
        title='Event Trend Over Time',
        height=height,
        xaxis_title='Time',
        yaxis_title='Number of Events',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_location_heatmap(health_matrix, height=500):
    """
    Create a heatmap of location health over time periods.
    
    Args:
        health_matrix (pandas.DataFrame): Matrix with locations as rows and time periods as columns
        height (int): Height of the chart
        
    Returns:
        plotly.graph_objects.Figure: Heatmap figure
    """
    if health_matrix.empty:
        return go.Figure()
    
    # Convert time buckets to hour labels
    bucket_labels = [f"Period {i+1}" for i in health_matrix.columns]
    
    # Create heatmap
    fig = px.imshow(
        health_matrix,
        labels=dict(x="Time Period", y="Location", color="Health Score"),
        x=bucket_labels,
        y=health_matrix.index,
        color_continuous_scale="RdYlGn",  # Red to Yellow to Green scale
        title="Location Health Over Time",
        height=height
    )
    
    # Update hover template
    fig.update_traces(
        hovertemplate="Location: %{y}<br>Time Period: %{x}<br>Health Score: %{z:.1f}<extra></extra>"
    )
    
    # Update layout
    fig.update_layout(
        coloraxis_colorbar=dict(
            title="Health Score",
            tickvals=[0, 25, 50, 75, 100],
            ticktext=["Critical", "Poor", "Fair", "Good", "Excellent"]
        )
    )
    
    return fig