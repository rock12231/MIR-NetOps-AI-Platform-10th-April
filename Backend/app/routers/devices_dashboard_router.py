# Backend/app/routers/devices_dashboard_router.py
import logging
import json
import os
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from qdrant_client.http import models
from qdrant_client.models import Filter, FieldCondition, Range, MatchValue
import pandas as pd
from io import StringIO

from app.core.config import qdrant
from app.utils.qdrant_utils import AVAILABLE_COLLECTIONS, parse_collection_name_backend

# Configure logger
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/devices", tags=["Devices Dashboard"])

# Path to metadata file
METADATA_PATH = os.path.join("data", "qdrant_db_metadata.json")

@router.get("/collections", response_model=List[str])
async def get_collections():
    """
    Get available collections from Qdrant.
    """
    try:
        collections = qdrant.get_collections().collections
        return [c.name for c in collections]
    except Exception as e:
        logger.error(f"Error getting collections: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting collections: {str(e)}")

@router.get("/device_data")
async def get_device_data(
    collection_name: str = Query(..., description="Name of the collection to query"),
    start_time: datetime = Query(..., description="Start time for filtering"),
    end_time: datetime = Query(..., description="End time for filtering"),
    device: Optional[str] = Query(None, description="Filter by device name"),
    location: Optional[str] = Query(None, description="Filter by location"),
    category: Optional[str] = Query(None, description="Filter by event category"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    interface: Optional[str] = Query(None, description="Filter by interface"),
    limit: int = Query(1000, description="Maximum number of records to return")
):
    """
    Fetch device data from Qdrant based on filters.
    """
    try:
        # Check if collection exists
        try:
            qdrant.get_collection(collection_name)
        except Exception as e:
            logger.error(f"Collection {collection_name} does not exist: {str(e)}")
            raise HTTPException(status_code=404, detail=f"Collection {collection_name} not found")
        
        # Build filter conditions
        must_conditions = []
        
        # Add timestamp filters
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())
        
        must_conditions.append(
            FieldCondition(
                key="timestamp",
                range=Range(
                    gte=start_timestamp,
                    lte=end_timestamp
                )
            )
        )
        
        # Add other filters if provided
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
        search_filter = Filter(must=must_conditions)
        
        # Execute the query
        search_result = qdrant.scroll(
            collection_name=collection_name,
            scroll_filter=search_filter,
            limit=limit,
            with_payload=True
        )
        
        # Convert to list of dictionaries
        records = [item.payload for item in search_result[0]]
        
        logger.info(f"Fetched {len(records)} records from collection {collection_name}")
        return {"data": records, "count": len(records)}
        
    except Exception as e:
        logger.error(f"Error in get_device_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching device data: {str(e)}")

@router.get("/interface_data")
async def get_interface_data(
    start_time: datetime = Query(..., description="Start time for filtering"),
    end_time: datetime = Query(..., description="End time for filtering"),
    device_type: str = Query(None, description="Filter by device type (e.g., agw)"),
    total_limit: int = Query(5000, description="Maximum total records")
):
    """
    Fetch interface-related data across collections.
    """
    try:
        # Get available collections
        collections = await get_collections()
        
        # Focus on collections related to the device type (primarily AGW for interfaces)
        if device_type:
            interface_collections = [c for c in collections if device_type.lower() in c.lower()]
        else:
            # Default to AGW collections
            interface_collections = [c for c in collections if 'agw' in c.lower()]
        
        if not interface_collections:
            return {"data": [], "count": 0, "message": f"No collections found for device type {device_type}"}
        
        # Calculate limit per collection
        per_collection_limit = total_limit // max(1, len(interface_collections))
        
        # Store all interface data
        all_data = []
        records_fetched = 0
        
        # Fetch data from each collection
        for collection_name in interface_collections:
            try:
                # Determine remaining limit
                remaining_limit = max(1, total_limit - records_fetched)
                
                # Fetch interface data from this collection
                device_data = await get_device_data(
                    collection_name=collection_name,
                    start_time=start_time,
                    end_time=end_time,
                    category="ETHPORT",  # Filter for interface-related events
                    limit=min(per_collection_limit, remaining_limit)
                )
                
                # Add to combined results
                if device_data["count"] > 0:
                    all_data.extend(device_data["data"])
                    records_fetched += device_data["count"]
                
                # Check if we've reached the limit
                if records_fetched >= total_limit:
                    logger.info(f"Reached total limit of {total_limit} records")
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching data from {collection_name}: {str(e)}")
                continue
        
        logger.info(f"Fetched {len(all_data)} interface events from {len(interface_collections)} collections")
        return {"data": all_data, "count": len(all_data)}
        
    except Exception as e:
        logger.error(f"Error in get_interface_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching interface data: {str(e)}") 