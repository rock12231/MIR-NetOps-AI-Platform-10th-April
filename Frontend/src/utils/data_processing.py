# src/utils/data_processing.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger


def detect_flapping_interfaces(df, time_threshold_minutes=30, min_transitions=3):
    """
    Identifies interfaces that are "flapping" (frequently changing state).
    
    Args:
        df (pandas.DataFrame): DataFrame containing interface events
        time_threshold_minutes (int): Maximum time between state changes to be considered flapping
        min_transitions (int): Minimum number of state transitions required
        
    Returns:
        pandas.DataFrame: DataFrame with flapping interfaces and their metrics
    """
    if df.empty or 'interface' not in df.columns:
        return pd.DataFrame()
    
    # Only consider interface events
    interface_events = df[df['interface'].notna()].copy()
    if interface_events.empty:
        return pd.DataFrame()
    
    # Ensure timestamp is datetime
    if 'timestamp_dt' not in interface_events.columns:
        if 'timestamp' in interface_events.columns:
            interface_events['timestamp_dt'] = pd.to_datetime(interface_events['timestamp'], unit='s')
        else:
            return pd.DataFrame()
    
    # Sort by interface and timestamp
    interface_events = interface_events.sort_values(['interface', 'timestamp_dt'])
    
    # Identify state changes (up/down events)
    flapping_interfaces = []
    
    # Group by interface
    for interface, group in interface_events.groupby('interface'):
        # Look for patterns of state changes
        state_changes = []
        for _, row in group.iterrows():
            if 'IF_UP' in str(row['event_type']):
                state_changes.append(('up', row['timestamp_dt'], row))
            elif 'IF_DOWN' in str(row['event_type']):
                state_changes.append(('down', row['timestamp_dt'], row))
        
        # If we have enough state changes
        if len(state_changes) >= min_transitions:
            # Check for consecutive transitions within time threshold
            time_diffs = []
            for i in range(len(state_changes) - 1):
                time_diff = (state_changes[i+1][1] - state_changes[i][1]).total_seconds() / 60
                time_diffs.append((state_changes[i][0], time_diff, state_changes[i][2], state_changes[i+1][2]))
            
            # Modified approach for consecutive transitions
            consecutive_flapping = False
            consecutive_count = 0
            
            for i in range(len(time_diffs)):
                if time_diffs[i][1] <= time_threshold_minutes:
                    consecutive_count += 1
                    if consecutive_count >= min_transitions - 1:
                        consecutive_flapping = True
                        break
                else:
                    consecutive_count = 0
            
            if consecutive_flapping:
                duration = (state_changes[-1][1] - state_changes[0][1]).total_seconds() / 60
                
                flapping_interfaces.append({
                    'interface': interface,
                    'transitions_count': len(state_changes),
                    'rapid_transitions': sum(1 for t in time_diffs if t[1] <= time_threshold_minutes),
                    'first_event': state_changes[0][1],
                    'last_event': state_changes[-1][1],
                    'total_duration_minutes': duration,
                    'transitions_per_hour': (len(state_changes) / (duration / 60)) if duration > 0 else 0,
                    'device': group['device'].iloc[0],
                    'location': group['location'].iloc[0],
                    'raw_logs': [r['raw_log'] for _, _, r in state_changes] if 'raw_log' in group.columns else [],
                    'category': group['category'].iloc[0] if 'category' in group.columns else None,
                })
    
    if not flapping_interfaces:
        return pd.DataFrame()
    
    return pd.DataFrame(flapping_interfaces)


def analyze_interface_stability(df, time_window_hours=24):
    """
    Calculate stability metrics for each interface.
    
    Args:
        df (pandas.DataFrame): DataFrame containing interface events
        time_window_hours (int): Time window for analysis in hours
        
    Returns:
        pandas.DataFrame: DataFrame with stability metrics for each interface
    """
    if df.empty or 'interface' not in df.columns:
        return pd.DataFrame()
    
    # Only consider interface events
    interface_events = df[df['interface'].notna()].copy()
    
    if interface_events.empty:
        return pd.DataFrame()
    
    # Ensure timestamp is datetime
    if 'timestamp_dt' not in interface_events.columns:
        if 'timestamp' in interface_events.columns:
            interface_events['timestamp_dt'] = pd.to_datetime(interface_events['timestamp'], unit='s')
        else:
            return pd.DataFrame()
    
    # Initialize stability metrics
    stability_metrics = []
    
    # Group by interface
    for interface, group in interface_events.groupby('interface'):
        # Count various event types
        up_events = sum('IF_UP' in str(event) for event in group['event_type'])
        down_events = sum('IF_DOWN' in str(event) for event in group['event_type'])
        config_events = sum(('DUPLEX' in str(event) or 'SPEED' in str(event) or 'FLOW_CONTROL' in str(event) 
                           or 'BANDWIDTH' in str(event)) for event in group['event_type'])
        total_events = len(group)
        
        # Calculate time span
        if len(group) > 1:
            time_span_hours = (group['timestamp_dt'].max() - group['timestamp_dt'].min()).total_seconds() / 3600
        else:
            time_span_hours = 0.1  # Avoid division by zero
        
        # Calculate effective time span (capped at time_window_hours)
        effective_time_span = min(time_span_hours, time_window_hours)
        
        # Calculate metrics
        event_frequency = total_events / effective_time_span if effective_time_span > 0 else 0
        down_ratio = down_events / total_events if total_events > 0 else 0
        
        # Calculate stability score (lower is worse)
        # Formula weights: 40% down ratio, 40% event frequency, 20% config changes
        stability_score = 100 - (
            40 * down_ratio + 
            40 * min(1, event_frequency / 5) +   # Cap at 5 events per hour
            20 * min(1, config_events / 5)       # Cap at 5 config changes
        )
        
        # Calculate flapping index (higher means more flapping)
        # Based on ratio of up/down events and their frequency
        flapping_index = 0
        if up_events > 0 and down_events > 0:
            # Perfect flapping would have equal up and down events
            up_down_ratio = min(up_events, down_events) / max(up_events, down_events)
            flapping_index = (up_events + down_events) * up_down_ratio / effective_time_span
        
        stability_metrics.append({
            'interface': interface,
            'device': group['device'].iloc[0],
            'location': group['location'].iloc[0],
            'total_events': total_events,
            'up_events': up_events,
            'down_events': down_events,
            'config_events': config_events,
            'time_span_hours': time_span_hours,
            'effective_time_span': effective_time_span,
            'event_frequency': event_frequency,
            'down_ratio': down_ratio,
            'stability_score': max(0, min(100, stability_score)),  # Ensure score is 0-100
            'flapping_index': flapping_index,
            'last_event': group['timestamp_dt'].max(),
            'first_event': group['timestamp_dt'].min()
        })
    
    if not stability_metrics:
        return pd.DataFrame()
    
    # Convert to DataFrame and sort by stability score
    metrics_df = pd.DataFrame(stability_metrics)
    metrics_df = metrics_df.sort_values('stability_score')
    
    return metrics_df


def categorize_interface_events(df):
    """
    Categorize interface events into appropriate types for analysis.
    
    Args:
        df (pandas.DataFrame): DataFrame containing interface events
        
    Returns:
        pandas.DataFrame: DataFrame with added 'event_category' column
    """
    if df.empty or 'event_type' not in df.columns:
        return df
    
    # Create a copy to avoid modifying the original
    result_df = df.copy()
    
    # Create event category column
    result_df['event_category'] = 'Other'
    
    # Categorize events
    # Status changes
    result_df.loc[result_df['event_type'].str.contains('IF_UP', na=False), 'event_category'] = 'Status Up'
    result_df.loc[result_df['event_type'].str.contains('IF_DOWN', na=False), 'event_category'] = 'Status Down'
    
    # Configuration changes
    result_df.loc[result_df['event_type'].str.contains('DUPLEX', na=False), 'event_category'] = 'Config Change'
    result_df.loc[result_df['event_type'].str.contains('SPEED', na=False), 'event_category'] = 'Config Change'
    result_df.loc[result_df['event_type'].str.contains('FLOW_CONTROL', na=False), 'event_category'] = 'Config Change'
    result_df.loc[result_df['event_type'].str.contains('BANDWIDTH', na=False), 'event_category'] = 'Config Change'
    
    # Further categorize down events
    result_df.loc[result_df['event_type'].str.contains('LINK_FAILURE', na=False), 'event_category'] = 'Link Failure'
    result_df.loc[result_df['event_type'].str.contains('ADMIN_DOWN', na=False), 'event_category'] = 'Admin Down'
    
    return result_df


def get_interface_timeline(df, interface=None):
    """
    Create a timeline of events for an interface or all interfaces.
    
    Args:
        df (pandas.DataFrame): DataFrame containing interface events
        interface (str, optional): Specific interface to analyze, or None for all
        
    Returns:
        pandas.DataFrame: DataFrame with timeline events
    """
    if df.empty or 'timestamp_dt' not in df.columns:
        return pd.DataFrame()
    
    # Filter for specific interface if requested
    if interface:
        df = df[df['interface'] == interface]
    
    # Only use events with interfaces
    df = df[df['interface'].notna()]
    
    if df.empty:
        return pd.DataFrame()
    
    # Sort by timestamp
    timeline_df = df.sort_values('timestamp_dt')
    
    # Add event category if not already there
    if 'event_category' not in timeline_df.columns:
        timeline_df = categorize_interface_events(timeline_df)
    
    return timeline_df


def calculate_interface_metrics(df, time_window_hours=24):
    """
    Calculate various metrics for interfaces in the given time window.
    
    Args:
        df (pandas.DataFrame): DataFrame containing interface events
        time_window_hours (int): Time window for analysis in hours
        
    Returns:
        dict: Dictionary with various interface metrics
    """
    if df.empty:
        return {
            'total_interfaces': 0,
            'active_interfaces': 0,
            'down_interfaces': 0,
            'flapping_interfaces': 0,
            'status_changes': 0,
            'config_changes': 0
        }
    
    # Calculate stability metrics
    stability_df = analyze_interface_stability(df, time_window_hours)
    
    # Detect flapping interfaces
    flapping_df = detect_flapping_interfaces(df)
    
    # Get interfaces with recent down events
    # For simplicity, we'll use interfaces with at least one down event in the time window
    interfaces_with_down = df[df['event_type'].str.contains('IF_DOWN', na=False)]['interface'].nunique() if 'event_type' in df.columns else 0
    
    # Count status and config changes
    status_changes = df[df['event_type'].str.contains('IF_UP|IF_DOWN', na=False)].shape[0] if 'event_type' in df.columns else 0
    config_changes = df[df['event_type'].str.contains('DUPLEX|SPEED|FLOW_CONTROL|BANDWIDTH', na=False)].shape[0] if 'event_type' in df.columns else 0
    
    # Calculate interface metrics
    total_interfaces = df['interface'].nunique()
    active_interfaces = df['interface'].nunique()  # All interfaces with any events
    down_interfaces = interfaces_with_down
    flapping_interfaces = flapping_df.shape[0] if not flapping_df.empty else 0
    
    return {
        'total_interfaces': total_interfaces,
        'active_interfaces': active_interfaces,
        'down_interfaces': down_interfaces,
        'flapping_interfaces': flapping_interfaces,
        'status_changes': status_changes,
        'config_changes': config_changes
    }

def calculate_network_health(df):
    """
    Calculate overall network health based on event severity distribution.
    
    Args:
        df (pandas.DataFrame): DataFrame with network events
        
    Returns:
        float: Health score percentage (0-100)
    """
    if df.empty or 'severity' not in df.columns:
        return 100.0  # Default to 100% if no data
    
    # Count events by severity
    severity_counts = df['severity'].value_counts().to_dict()
    
    # Define severity weights (higher severity = more impact)
    weights = {
        '0': 100,  # Emergency
        '1': 80,   # Alert
        '2': 60,   # Critical
        '3': 40,   # Error
        '4': 20,   # Warning
        '5': 5,    # Notice
        '6': 1     # Info
    }
    
    # Calculate weighted severity score
    total_events = len(df)
    weighted_sum = sum(weights.get(str(sev), 0) * count for sev, count in severity_counts.items())
    max_possible = total_events * 100  # Max weight (100) for all events
    
    # Calculate health (100% - normalized weighted score)
    if max_possible > 0:
        health_score = 100 - (weighted_sum / max_possible * 100)
    else:
        health_score = 100
    
    return max(0, min(100, health_score))

def analyze_device_distribution(df):
    """
    Analyze the distribution of devices across locations and types.
    
    Args:
        df (pandas.DataFrame): DataFrame with network events
        
    Returns:
        dict: Dictionary with device distribution data
    """
    if df.empty:
        return {
            "by_type": pd.DataFrame(),
            "by_location": pd.DataFrame(),
            "by_type_location": pd.DataFrame()
        }
    
    # Calculate distribution by device type
    by_type = df.groupby('device_type').size().reset_index(name='count')
    
    # Calculate distribution by location
    by_location = df.groupby('location').size().reset_index(name='count')
    
    # Calculate distribution by device type and location
    by_type_location = df.groupby(['device_type', 'location']).size().reset_index(name='count')
    
    return {
        "by_type": by_type,
        "by_location": by_location,
        "by_type_location": by_type_location
    }

def create_location_health_matrix(df, time_window=24):
    """
    Create a matrix of health metrics by location and time.
    
    Args:
        df (pandas.DataFrame): DataFrame with network events
        time_window (int): Time window in hours to analyze
        
    Returns:
        pandas.DataFrame: Matrix with locations as rows and time periods as columns
    """
    if df.empty or 'timestamp_dt' not in df.columns or 'location' not in df.columns:
        return pd.DataFrame()
    
    # Get time range and create hour bins
    min_time = df['timestamp_dt'].min()
    max_time = df['timestamp_dt'].max()
    time_range = max_time - min_time
    hours = int(time_range.total_seconds() / 3600) + 1
    
    # Limit to maximum 12 time buckets for readability
    num_buckets = min(12, hours)
    bucket_size_hours = max(1, hours // num_buckets)
    
    # Create time buckets
    df['time_bucket'] = ((df['timestamp_dt'] - min_time).dt.total_seconds() / 3600 / bucket_size_hours).astype(int)
    
    # Calculate health impact by severity
    severity_impact = {
        '0': 100,  # Emergency
        '1': 80,   # Alert
        '2': 60,   # Critical
        '3': 40,   # Error
        '4': 20,   # Warning
        '5': 5,    # Notice
        '6': 1     # Info
    }
    
    # Create severity impact column
    df['severity_impact'] = df['severity'].map(lambda x: severity_impact.get(str(x), 5))
    
    # Group by location and time bucket, calculate health score
    health_matrix = df.groupby(['location', 'time_bucket'])['severity_impact'].agg(['sum', 'count']).reset_index()
    
    # Calculate health score (inversely proportional to severity impact)
    health_matrix['health_score'] = 100 - (health_matrix['sum'] / health_matrix['count']).clip(0, 100)
    
    # Create pivot table
    pivot = health_matrix.pivot(index='location', columns='time_bucket', values='health_score')
    
    # Fill NaN with 100 (perfect health where no events)
    pivot = pivot.fillna(100)
    
    return pivot