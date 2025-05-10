# src/utils/qdrant_client.py
"""
Qdrant client utilities for the Network Monitoring Dashboard.
Provides common functionality for connecting to and querying the Qdrant database.
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
import streamlit as st
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.models import Filter, FieldCondition, Range, MatchValue
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
import pandas as pd


# Configuration
QDRANT_HOST = os.getenv('QDRANT_HOST', 'localhost')
QDRANT_PORT = int(os.getenv('QDRANT_PORT', '6333'))
METADATA_PATH = os.getenv('METADATA_PATH', 'data/qdrant_db_metadata.json')
CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
def create_qdrant_client():
    """
    Create and test connection to Qdrant client with retry logic.
    
    Returns:
        QdrantClient: Connected Qdrant client
    
    Raises:
        Exception: If connection fails after MAX_RETRIES
    """
    try:
        # Attempt connection
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        # Test the connection
        client.get_collections()
        logger.info(f"Successfully connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}: {str(e)}")
        raise


def health_check() -> Tuple[bool, str]:
    """
    Check the health of the Qdrant connection.
    
    Returns:
        Tuple[bool, str]: A tuple containing:
            - bool: True if healthy, False otherwise
            - str: Status message
    """
    try:
        client = get_qdrant_client()
        # Test the connection by getting collections
        collections = client.get_collections()
        collection_count = len(collections.collections)
        return True, f"Connected to Qdrant. Found {collection_count} collections."
    except Exception as e:
        error_msg = f"Failed to connect to Qdrant: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


@st.cache_resource(ttl=3600)
def get_qdrant_client():
    """
    Get or create a cached Qdrant client.
    
    Returns:
        QdrantClient: Cached Qdrant client
    """
    return create_qdrant_client()


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
    Get default metadata structure when the metadata file is missing or invalid.
    
    Returns:
        dict: Default empty metadata structure
    """
    logger.info("Using default metadata configuration")
    return {
        "collections": [],
        "agw": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": []},
        "dgw": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": []},
        "fw": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": [], "processes": []},
        "vadc": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": []}
    }


@st.cache_data(ttl=CACHE_TTL)
def get_collections():
    """
    Get available collections from Qdrant.
    
    Returns:
        list: List of collection names
    """
    try:
        client = get_qdrant_client()
        collections = client.get_collections().collections
        return [c.name for c in collections]
    except Exception as e:
        logger.error(f"Error getting collections: {str(e)}")
        return []


@st.cache_data(ttl=CACHE_TTL)
def fetch_data(collection_name, start_time=None, end_time=None, limit=1000, 
              device=None, location=None, category=None, event_type=None, 
              severity=None, interface=None):
    """
    Fetch data from Qdrant based on filters.
    
    Args:
        collection_name (str): Name of the collection to query
        start_time (datetime, optional): Start time for filtering
        end_time (datetime, optional): End time for filtering
        limit (int, optional): Maximum number of records to return. Defaults to 1000.
        device (str, optional): Filter by device name
        location (str, optional): Filter by location
        category (str, optional): Filter by event category
        event_type (str, optional): Filter by event type
        severity (str, optional): Filter by severity
        interface (str, optional): Filter by interface name
        
    Returns:
        pandas.DataFrame: Dataframe containing filtered records
    """
    try:
        client = get_qdrant_client()
        
        # Check if collection exists
        try:
            client.get_collection(collection_name)
        except Exception as e:
            logger.error(f"Collection {collection_name} does not exist: {str(e)}")
            return pd.DataFrame()
        
        must_conditions = []
        
        # Add timestamp filters
        if start_time:
            must_conditions.append(
                FieldCondition(
                    key="timestamp",
                    range=Range(
                        gte=int(start_time.timestamp())
                    )
                )
            )
        
        if end_time:
            must_conditions.append(
                FieldCondition(
                    key="timestamp",
                    range=Range(
                        lte=int(end_time.timestamp())
                    )
                )
            )
        
        # Add other filters
        if device:
            must_conditions.append(
                FieldCondition(
                    key="device",
                    match=MatchValue(value=device)
                )
            )
        
        if location:
            must_conditions.append(
                FieldCondition(
                    key="location",
                    match=MatchValue(value=location)
                )
            )
        
        if category:
            must_conditions.append(
                FieldCondition(
                    key="category",
                    match=MatchValue(value=category)
                )
            )
        
        if event_type:
            must_conditions.append(
                FieldCondition(
                    key="event_type",
                    match=MatchValue(value=event_type)
                )
            )
        
        if severity:
            must_conditions.append(
                FieldCondition(
                    key="severity",
                    match=MatchValue(value=severity)
                )
            )
        
        if interface:
            must_conditions.append(
                FieldCondition(
                    key="interface",
                    match=MatchValue(value=interface)
                )
            )
        
        # Create filter
        search_filter = Filter(
            must=must_conditions
        ) if must_conditions else None
        
        # Execute the query
        try:
            search_result = client.scroll(
                collection_name=collection_name,
                scroll_filter=search_filter,
                limit=limit,
                with_payload=True
            )
            
            # Convert to DataFrame
            records = [item.payload for item in search_result[0]]
            
            if not records:
                logger.info(f"No records found in collection {collection_name} with the specified filters")
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            
            # Convert timestamp to datetime if present
            if 'timestamp' in df.columns:
                df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='s')
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data from collection {collection_name}: {str(e)}")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Unexpected error in fetch_data: {str(e)}")
        return pd.DataFrame()


def get_interface_collections():
    """
    Get collections that are related to interfaces (primarily AGW).
    
    Returns:
        list: List of collection names that likely contain interface data
    """
    collections = get_collections()
    # Focus on AGW collections which typically have interface data
    interface_collections = [c for c in collections if 'agw' in c.lower()]
    return interface_collections


def fetch_all_interface_data(start_time, end_time, total_limit=10000):
    """
    Fetch all interface-related data across collections with optimized limit handling.
    
    Args:
        start_time (datetime): Start time for filtering
        end_time (datetime): End time for filtering
        total_limit (int, optional): Maximum total records to fetch. Defaults to 10000.
        
    Returns:
        pandas.DataFrame: Combined dataframe with all interface data
    """
    interface_collections = get_interface_collections()
    all_data = []
    records_fetched = 0
    
    # Calculate per-collection limit
    per_collection_limit = total_limit // max(1, len(interface_collections))
    
    for collection_name in interface_collections:
        remaining_limit = max(1, total_limit - records_fetched)
        # Get data from this collection with adjusted limit
        df = fetch_data(
            collection_name=collection_name,
            start_time=start_time,
            end_time=end_time,
            limit=min(per_collection_limit, remaining_limit),
            category="ETHPORT"  # Filter for interface-related events
        )
        
        if not df.empty:
            all_data.append(df)
            records_fetched += len(df)
            
        if records_fetched >= total_limit:
            logger.info(f"Reached total limit of {total_limit} records")
            break
    
    # Combine all dataframes
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        logger.info(f"Fetched {len(combined_df)} interface events from {len(all_data)} collections")
        return combined_df
    else:
        logger.warning("No interface data found")
        return pd.DataFrame()

def fetch_aggregated_network_data(start_time, end_time, device_types=None, locations=None, limit_per_collection=200):
    """
    Fetch data across multiple collections for network-wide analysis.
    
    Args:
        start_time (datetime): Start time for filtering
        end_time (datetime): End time for filtering
        device_types (list, optional): List of device types to include
        locations (list, optional): List of locations to include
        limit_per_collection (int): Limit records per collection to prevent overload
        
    Returns:
        pandas.DataFrame: Combined dataframe with data from all relevant collections
    """
    # Get list of collections
    all_collections = get_collections()
    
    # Filter collections based on device types if specified
    if device_types:
        filtered_collections = []
        for col in all_collections:
            for device_type in device_types:
                if device_type.lower() in col.lower():
                    filtered_collections.append(col)
                    break
        collections = filtered_collections
    else:
        collections = all_collections
    
    # Prepare to store data from each collection
    all_data = []
    
    # Fetch data from each collection
    for collection_name in collections:
        try:
            # Parse device and location from collection name
            parts = collection_name.replace("router_", "").replace("_vector", "").split("_")
            if len(parts) < 3:
                continue
                
            if parts[-1] not in ["log", "config"]:
                continue
                
            # Extract device name and location
            if parts[0] == "new" and len(parts) > 3:
                device = f"{parts[0]}_{parts[1]}"
                location = "_".join(parts[2:-1])
            else:
                device = parts[0]
                location = "_".join(parts[1:-1])
            
            # Skip if location filtering is active and this location isn't included
            if locations and location not in locations:
                continue
            
            # Fetch data with device/location already embedded in collection name
            df = fetch_data(
                collection_name=collection_name,
                start_time=start_time,
                end_time=end_time,
                limit=limit_per_collection
            )
            
            if not df.empty:
                # Add device type explicitly
                if device.startswith('agw'):
                    df['device_type'] = 'agw'
                elif device.startswith('dgw'):
                    df['device_type'] = 'dgw'
                elif device.startswith('fw') or device.startswith('new_fw'):
                    df['device_type'] = 'fw'
                elif device.startswith('vadc'):
                    df['device_type'] = 'vadc'
                else:
                    df['device_type'] = 'unknown'
                
                all_data.append(df)
                
        except Exception as e:
            logger.error(f"Error fetching data from {collection_name}: {str(e)}")
            continue
    
    # Combine all dataframes
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        logger.info(f"Fetched {len(combined_df)} events from {len(all_data)} collections")
        return combined_df
    else:
        logger.warning("No data found across collections")
        return pd.DataFrame()