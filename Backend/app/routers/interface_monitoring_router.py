# Backend/app/routers/interface_monitoring_router.py
import logging
import json
import os
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from qdrant_client.http import models
from qdrant_client.models import Filter, FieldCondition, Range, MatchValue
import pandas as pd
import numpy as np
from io import StringIO

from app.core.config import qdrant
from app.utils.qdrant_utils import AVAILABLE_COLLECTIONS, parse_collection_name_backend

# Configure logger
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/interfaces", tags=["Interface Monitoring"])

# Path to metadata file
METADATA_PATH = os.path.join("data", "qdrant_db_metadata.json")

@router.get("/collections", response_model=List[str])
async def get_interface_collections(device_type: str = Query("agw", description="Filter collections by device type")):
    """
    Get collections that are related to interfaces (primarily AGW).
    
    Returns:
        list: List of collection names that likely contain interface data
    """
    try:
        # Convert query parameter to string
        device_type_str = str(device_type) if device_type is not None else "agw"
        
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]
        
        # Focus on collections related to the specified device type (primarily AGW for interfaces)
        interface_collections = [c for c in collection_names if device_type_str.lower() in c.lower()]
        
        return interface_collections
    except Exception as e:
        logger.error(f"Error getting interface collections: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting interface collections: {str(e)}")

@router.get("/interface_data")
async def get_interface_data(
    start_time: datetime = Query(..., description="Start time for filtering"),
    end_time: datetime = Query(..., description="End time for filtering"),
    device: Optional[str] = Query(None, description="Filter by device name"),
    location: Optional[str] = Query(None, description="Filter by location"),
    interface: Optional[str] = Query(None, description="Filter by interface name"),
    total_limit: int = Query(10000, description="Maximum total records to return")
):
    """
    Fetch interface events data from Qdrant across collections.
    
    Args:
        start_time: Start time for filtering
        end_time: End time for filtering
        device: Filter by device name
        location: Filter by location
        interface: Filter by interface name
        total_limit: Maximum number of records to return
        
    Returns:
        Dict containing interface events data
    """
    try:
        # Safely get the integer value - use the raw value, not the Query object
        total_limit_int = 10000  # Default value
        if isinstance(total_limit, int):
            total_limit_int = total_limit
        
        # Convert string parameters to actual strings
        device_str = str(device) if device is not None else None
        location_str = str(location) if location is not None else None
        interface_str = str(interface) if interface is not None else None
        
        # Determine collection to query
        if device_str and location_str:
            # If both device and location are specified, we can target a specific collection
            collection_name = f"router_{device_str}_{location_str}_log_vector"
            collections = [collection_name]
        else:
            # Otherwise, get all interface-related collections
            collections = await get_interface_collections()
            
            # Filter by device if provided
            if device_str:
                collections = [c for c in collections if device_str.lower() in c.lower()]
                
            # Filter by location if provided
            if location_str:
                collections = [c for c in collections if location_str.lower() in c.lower()]
        
        if not collections:
            return {"data": [], "count": 0, "message": "No matching collections found"}
        
        # Calculate per-collection limit using plain integers
        per_collection_limit = total_limit_int // max(1, len(collections))
        
        # Store all interface data
        all_data = []
        records_fetched = 0
        
        # Fetch data from each collection
        for collection_name in collections:
            try:
                # Create filter conditions
                must_conditions = [
                    # Add timestamp filters
                    FieldCondition(
                        key="timestamp",
                        range=Range(
                            gte=int(start_time.timestamp()),
                            lte=int(end_time.timestamp())
                        )
                    ),
                    # Filter for interface events (ETHPORT category)
                    FieldCondition(
                        key="category",
                        match=MatchValue(value="ETHPORT")
                    )
                ]
                
                # Add interface filter if specified
                if interface_str:
                    must_conditions.append(
                        FieldCondition(
                            key="interface",
                            match=MatchValue(value=interface_str)
                        )
                    )
                
                # Create filter
                search_filter = Filter(must=must_conditions)
                
                # Calculate remaining limit using plain integers
                remaining_limit = max(1, total_limit_int - records_fetched)
                current_limit = min(per_collection_limit, remaining_limit)
                
                try:
                    # Check if collection exists
                    qdrant.get_collection(collection_name)
                    
                    # Execute the query
                    search_result = qdrant.scroll(
                        collection_name=collection_name,
                        scroll_filter=search_filter,
                        limit=current_limit,
                        with_payload=True
                    )
                    
                    # Convert to list of dictionaries
                    records = [item.payload for item in search_result[0]]
                    
                    if records:
                        # Parse device and location from collection name if not in records
                        device_type, device_id, loc, _ = parse_collection_name_backend(collection_name)
                        
                        # Add device, device_type, and location if not present
                        for record in records:
                            if 'device' not in record:
                                record['device'] = device_id
                            if 'device_type' not in record:
                                record['device_type'] = device_type
                            if 'location' not in record:
                                record['location'] = loc
                        
                        all_data.extend(records)
                        records_fetched += len(records)
                        
                        # If we've reached the limit, stop fetching
                        if records_fetched >= total_limit_int:
                            logger.info(f"Reached total limit of {total_limit_int} records")
                            break
                except Exception as e:
                    logger.warning(f"Collection {collection_name} not found or error querying: {str(e)}")
                    continue
                    
            except Exception as e:
                logger.error(f"Error fetching data from {collection_name}: {str(e)}")
                continue
        
        if not all_data:
            return {"data": [], "count": 0, "message": "No interface data found with the specified filters"}
            
        logger.info(f"Fetched {len(all_data)} interface events")
        return {"data": all_data, "count": len(all_data)}
        
    except Exception as e:
        logger.error(f"Error in get_interface_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching interface data: {str(e)}")

@router.get("/detect_flapping")
async def detect_flapping_interfaces(
    start_time: datetime = Query(..., description="Start time for filtering"),
    end_time: datetime = Query(..., description="End time for filtering"),
    device: Optional[str] = Query(None, description="Filter by device name"),
    location: Optional[str] = Query(None, description="Filter by location"),
    interface: Optional[str] = Query(None, description="Filter by interface name"),
    time_threshold_minutes: int = Query(30, description="Maximum time between state changes to be considered flapping"),
    min_transitions: int = Query(3, description="Minimum number of state transitions required")
):
    """
    Identifies interfaces that are "flapping" (frequently changing state).
    
    Args:
        start_time: Start time for filtering
        end_time: End time for filtering
        device: Filter by device name
        location: Filter by location
        interface: Filter by interface name
        time_threshold_minutes: Maximum time between state changes to be considered flapping
        min_transitions: Minimum number of state transitions required
        
    Returns:
        Dict containing flapping interfaces data
    """
    try:
        # Get the integer values directly
        time_threshold_min = 30  # Default value
        min_transitions_count = 3  # Default value
        
        if isinstance(time_threshold_minutes, int):
            time_threshold_min = time_threshold_minutes
            
        if isinstance(min_transitions, int):
            min_transitions_count = min_transitions
        
        # Convert string parameters to actual strings
        device_str = str(device) if device is not None else None
        location_str = str(location) if location is not None else None
        interface_str = str(interface) if interface is not None else None
        
        # First get the interface data
        interface_data_response = await get_interface_data(
            start_time=start_time,
            end_time=end_time,
            device=device_str,
            location=location_str,
            interface=interface_str
        )
        
        if not interface_data_response["data"]:
            return {"data": [], "count": 0, "message": "No interface data found to analyze"}
            
        # Convert to DataFrame
        df = pd.DataFrame(interface_data_response["data"])
        
        # Ensure required columns exist
        if 'interface' not in df.columns:
            return {"data": [], "count": 0, "message": "Interface column not found in data"}
            
        # Create timestamp_dt column if needed
        if 'timestamp_dt' not in df.columns and 'timestamp' in df.columns:
            df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='s')
            
        # Identify flapping interfaces
        flapping_interfaces = []
        
        # Group by interface
        for interface_name, group in df.groupby('interface'):
            # Sort by timestamp
            group = group.sort_values('timestamp_dt')
            
            # Look for patterns of state changes (up/down events)
            state_changes = []
            for _, row in group.iterrows():
                if 'IF_UP' in str(row['event_type']):
                    state_changes.append(('up', row['timestamp_dt'], row))
                elif 'IF_DOWN' in str(row['event_type']):
                    state_changes.append(('down', row['timestamp_dt'], row))
            
            # If we have enough state changes
            if len(state_changes) >= min_transitions_count:
                # Check for consecutive transitions within time threshold
                time_diffs = []
                for i in range(len(state_changes) - 1):
                    time_diff = (state_changes[i+1][1] - state_changes[i][1]).total_seconds() / 60
                    time_diffs.append((state_changes[i][0], time_diff, state_changes[i][2], state_changes[i+1][2]))
                
                # Check for consecutive transitions
                consecutive_flapping = False
                consecutive_count = 0
                
                for i in range(len(time_diffs)):
                    if time_diffs[i][1] <= time_threshold_min:
                        consecutive_count += 1
                        if consecutive_count >= min_transitions_count - 1:
                            consecutive_flapping = True
                            break
                    else:
                        consecutive_count = 0
                
                if consecutive_flapping:
                    duration = (state_changes[-1][1] - state_changes[0][1]).total_seconds() / 60
                    
                    flapping_interfaces.append({
                        'interface': interface_name,
                        'transitions_count': len(state_changes),
                        'rapid_transitions': sum(1 for t in time_diffs if t[1] <= time_threshold_min),
                        'first_event': state_changes[0][1].isoformat(),
                        'last_event': state_changes[-1][1].isoformat(),
                        'total_duration_minutes': duration,
                        'transitions_per_hour': (len(state_changes) / (duration / 60)) if duration > 0 else 0,
                        'device': group['device'].iloc[0],
                        'location': group['location'].iloc[0] if 'location' in group.columns else None,
                        'category': group['category'].iloc[0] if 'category' in group.columns else None,
                    })
        
        return {"data": flapping_interfaces, "count": len(flapping_interfaces)}
        
    except Exception as e:
        logger.error(f"Error in detect_flapping_interfaces: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error detecting flapping interfaces: {str(e)}")

@router.get("/analyze_stability")
async def analyze_interface_stability(
    start_time: datetime = Query(..., description="Start time for filtering"),
    end_time: datetime = Query(..., description="End time for filtering"),
    device: Optional[str] = Query(None, description="Filter by device name"),
    location: Optional[str] = Query(None, description="Filter by location"),
    interface: Optional[str] = Query(None, description="Filter by interface name"),
    time_window_hours: int = Query(24, description="Time window for analysis in hours")
):
    """
    Calculate stability metrics for each interface.
    
    Args:
        start_time: Start time for filtering
        end_time: End time for filtering
        device: Filter by device name
        location: Filter by location
        interface: Filter by interface name
        time_window_hours: Time window for analysis in hours
        
    Returns:
        Dict containing interface stability metrics
    """
    try:
        # Get the integer value directly
        window_hours = 24  # Default value
        if isinstance(time_window_hours, int):
            window_hours = time_window_hours
            
        # Convert string parameters to actual strings
        device_str = str(device) if device is not None else None
        location_str = str(location) if location is not None else None
        interface_str = str(interface) if interface is not None else None
        
        # First get the interface data
        interface_data_response = await get_interface_data(
            start_time=start_time,
            end_time=end_time,
            device=device_str,
            location=location_str,
            interface=interface_str
        )
        
        if not interface_data_response["data"]:
            return {"data": [], "count": 0, "message": "No interface data found to analyze"}
            
        # Convert to DataFrame
        df = pd.DataFrame(interface_data_response["data"])
        
        # Ensure required columns exist
        if 'interface' not in df.columns:
            return {"data": [], "count": 0, "message": "Interface column not found in data"}
            
        # Create timestamp_dt column if needed
        if 'timestamp_dt' not in df.columns and 'timestamp' in df.columns:
            df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='s')
            
        # Initialize stability metrics
        stability_metrics = []
        
        # Group by interface
        for interface_name, group in df.groupby('interface'):
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
            effective_time_span = min(time_span_hours, window_hours)
            
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
                'interface': interface_name,
                'device': group['device'].iloc[0],
                'location': group['location'].iloc[0] if 'location' in group.columns else None,
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
                'last_event': group['timestamp_dt'].max().isoformat(),
                'first_event': group['timestamp_dt'].min().isoformat()
            })
        
        return {"data": stability_metrics, "count": len(stability_metrics)}
        
    except Exception as e:
        logger.error(f"Error in analyze_interface_stability: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing interface stability: {str(e)}")

@router.get("/interface_metrics")
async def calculate_interface_metrics(
    start_time: datetime = Query(..., description="Start time for filtering"),
    end_time: datetime = Query(..., description="End time for filtering"),
    device: Optional[str] = Query(None, description="Filter by device name"),
    location: Optional[str] = Query(None, description="Filter by location"),
    time_window_hours: int = Query(24, description="Time window for analysis in hours")
):
    """
    Calculate various metrics for interfaces in the given time window.
    
    Args:
        start_time: Start time for filtering
        end_time: End time for filtering
        device: Filter by device name
        location: Filter by location
        time_window_hours: Time window for analysis in hours
        
    Returns:
        Dict with various interface metrics
    """
    try:
        # Get the integer value directly
        window_hours = 24  # Default value
        if isinstance(time_window_hours, int):
            window_hours = time_window_hours
            
        # Convert string parameters to actual strings
        device_str = str(device) if device is not None else None
        location_str = str(location) if location is not None else None
        
        # First get the interface data
        interface_data_response = await get_interface_data(
            start_time=start_time,
            end_time=end_time,
            device=device_str,
            location=location_str
        )
        
        if not interface_data_response["data"]:
            return {
                "total_interfaces": 0,
                "active_interfaces": 0,
                "down_interfaces": 0,
                "flapping_interfaces": 0,
                "status_changes": 0,
                "config_changes": 0,
                "message": "No interface data found to analyze"
            }
            
        # Convert to DataFrame
        df = pd.DataFrame(interface_data_response["data"])
        
        # Analyze stability for metrics
        stability_response = await analyze_interface_stability(
            start_time=start_time,
            end_time=end_time,
            device=device_str,
            location=location_str,
            time_window_hours=window_hours
        )
        
        # Detect flapping interfaces
        flapping_response = await detect_flapping_interfaces(
            start_time=start_time,
            end_time=end_time,
            device=device_str,
            location=location_str
        )
        
        # Get interfaces with recent down events
        # For simplicity, we'll use interfaces with at least one down event in the time window
        interfaces_with_down = len(df[df['event_type'].str.contains('IF_DOWN', na=False)]['interface'].unique()) if 'event_type' in df.columns else 0
        
        # Count status and config changes
        status_changes = df[df['event_type'].str.contains('IF_UP|IF_DOWN', na=False)].shape[0] if 'event_type' in df.columns else 0
        config_changes = df[df['event_type'].str.contains('DUPLEX|SPEED|FLOW_CONTROL|BANDWIDTH', na=False)].shape[0] if 'event_type' in df.columns else 0
        
        # Calculate interface metrics
        total_interfaces = df['interface'].nunique()
        active_interfaces = df['interface'].nunique()  # All interfaces with any events
        down_interfaces = interfaces_with_down
        flapping_interfaces = flapping_response["count"] if "count" in flapping_response else 0
        
        return {
            'total_interfaces': total_interfaces,
            'active_interfaces': active_interfaces,
            'down_interfaces': down_interfaces,
            'flapping_interfaces': flapping_interfaces,
            'status_changes': status_changes,
            'config_changes': config_changes
        }
        
    except Exception as e:
        logger.error(f"Error in calculate_interface_metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error calculating interface metrics: {str(e)}")

@router.get("/categorize_events")
async def categorize_interface_events(
    start_time: datetime = Query(..., description="Start time for filtering"),
    end_time: datetime = Query(..., description="End time for filtering"),
    device: Optional[str] = Query(None, description="Filter by device name"),
    location: Optional[str] = Query(None, description="Filter by location"),
    interface: Optional[str] = Query(None, description="Filter by interface name")
):
    """
    Categorize interface events into appropriate types for analysis.
    
    Args:
        start_time: Start time for filtering
        end_time: End time for filtering
        device: Filter by device name
        location: Filter by location
        interface: Filter by interface name
        
    Returns:
        Dict with categorized interface events
    """
    try:
        # Convert string parameters to actual strings
        device_str = str(device) if device is not None else None
        location_str = str(location) if location is not None else None
        interface_str = str(interface) if interface is not None else None
        
        # First get the interface data
        interface_data_response = await get_interface_data(
            start_time=start_time,
            end_time=end_time,
            device=device_str,
            location=location_str,
            interface=interface_str
        )
        
        if not interface_data_response["data"]:
            return {"data": [], "count": 0, "message": "No interface data found to categorize"}
            
        # Convert to DataFrame
        df = pd.DataFrame(interface_data_response["data"])
        
        # Ensure event_type column exists
        if 'event_type' not in df.columns:
            return {"data": [], "count": 0, "message": "Event type column not found in data"}
        
        # Create event category column
        df['event_category'] = 'Other'
        
        # Categorize events
        # Status changes
        df.loc[df['event_type'].str.contains('IF_UP', na=False), 'event_category'] = 'Status Up'
        df.loc[df['event_type'].str.contains('IF_DOWN', na=False), 'event_category'] = 'Status Down'
        
        # Configuration changes
        df.loc[df['event_type'].str.contains('DUPLEX', na=False), 'event_category'] = 'Config Change'
        df.loc[df['event_type'].str.contains('SPEED', na=False), 'event_category'] = 'Config Change'
        df.loc[df['event_type'].str.contains('FLOW_CONTROL', na=False), 'event_category'] = 'Config Change'
        df.loc[df['event_type'].str.contains('BANDWIDTH', na=False), 'event_category'] = 'Config Change'
        
        # Further categorize down events
        df.loc[df['event_type'].str.contains('LINK_FAILURE', na=False), 'event_category'] = 'Link Failure'
        df.loc[df['event_type'].str.contains('ADMIN_DOWN', na=False), 'event_category'] = 'Admin Down'
        
        # Convert data back to dict
        categorized_data = df.to_dict(orient='records')
        
        return {"data": categorized_data, "count": len(categorized_data)}
        
    except Exception as e:
        logger.error(f"Error in categorize_interface_events: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error categorizing interface events: {str(e)}") 