# Backend/app/routers/devices_dashboard_router.py
import logging
import json
import os
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends
from qdrant_client.http import models
from qdrant_client.models import Filter, FieldCondition, Range, MatchValue
import pandas as pd
from io import StringIO

from app.core.config import qdrant
from app.utils.qdrant_utils import AVAILABLE_COLLECTIONS, parse_collection_name_backend
from app.core.models import DeviceDataRequest, InterfaceDataRequest, DeviceDataResponse

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

@router.get("/device_data", response_model=DeviceDataResponse)
async def get_device_data(
    request: DeviceDataRequest = Depends()
):
    """
    Fetch device data from Qdrant based on filters.
    """
    try:
        # Check if collection exists
        try:
            qdrant.get_collection(request.collection_name)
        except Exception as e:
            logger.error(f"Collection {request.collection_name} does not exist: {str(e)}")
            raise HTTPException(status_code=404, detail=f"Collection {request.collection_name} not found")
        
        # Build filter conditions
        must_conditions = []
        
        # Add timestamp filters
        start_timestamp = int(request.start_time.timestamp())
        end_timestamp = int(request.end_time.timestamp())
        
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
        if request.device:
            must_conditions.append(
                FieldCondition(
                    key="device",
                    match=MatchValue(value=request.device)
                )
            )
        
        if request.location:
            must_conditions.append(
                FieldCondition(
                    key="location",
                    match=MatchValue(value=request.location)
                )
            )
        
        if request.category:
            must_conditions.append(
                FieldCondition(
                    key="category",
                    match=MatchValue(value=request.category)
                )
            )
        
        if request.event_type:
            must_conditions.append(
                FieldCondition(
                    key="event_type",
                    match=MatchValue(value=request.event_type)
                )
            )
        
        if request.severity:
            must_conditions.append(
                FieldCondition(
                    key="severity",
                    match=MatchValue(value=request.severity)
                )
            )
        
        if request.interface:
            must_conditions.append(
                FieldCondition(
                    key="interface",
                    match=MatchValue(value=request.interface)
                )
            )
        
        # Create filter
        search_filter = Filter(must=must_conditions)
        
        # Execute the query
        search_result = qdrant.scroll(
            collection_name=request.collection_name,
            scroll_filter=search_filter,
            limit=request.limit,
            with_payload=True
        )
        
        # Convert to list of dictionaries
        records = [item.payload for item in search_result[0]]
        
        logger.info(f"Fetched {len(records)} records from collection {request.collection_name}")
        return DeviceDataResponse(data=records, count=len(records))
        
    except Exception as e:
        logger.error(f"Error in get_device_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching device data: {str(e)}")

@router.get("/interface_data", response_model=DeviceDataResponse)
async def get_interface_data(
    request: InterfaceDataRequest = Depends()
):
    """
    Fetch interface-related data across collections.
    """
    try:
        # Get available collections
        collections = await get_collections()
        
        # Focus on collections related to the device type (primarily AGW for interfaces)
        if request.device_type:
            interface_collections = [c for c in collections if request.device_type.lower() in c.lower()]
        else:
            # Default to AGW collections
            interface_collections = [c for c in collections if 'agw' in c.lower()]
        
        if not interface_collections:
            return DeviceDataResponse(
                data=[], 
                count=0, 
                message=f"No collections found for device type {request.device_type}"
            )
        
        # Calculate limit per collection
        per_collection_limit = request.total_limit // max(1, len(interface_collections))
        
        # Store all interface data
        all_data = []
        records_fetched = 0
        
        # Fetch data from each collection
        for collection_name in interface_collections:
            try:
                # Determine remaining limit
                remaining_limit = max(1, request.total_limit - records_fetched)
                
                # Create device data request
                device_req = DeviceDataRequest(
                    collection_name=collection_name,
                    start_time=request.start_time,
                    end_time=request.end_time,
                    category="ETHPORT",  # Filter for interface-related events
                    limit=min(per_collection_limit, remaining_limit)
                )
                
                # Fetch interface data from this collection
                device_data = await get_device_data(device_req)
                
                # Add to combined results
                if device_data.count > 0:
                    all_data.extend(device_data.data)
                    records_fetched += device_data.count
                
                # Check if we've reached the limit
                if records_fetched >= request.total_limit:
                    logger.info(f"Reached total limit of {request.total_limit} records")
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching data from {collection_name}: {str(e)}")
                continue
        
        logger.info(f"Fetched {len(all_data)} interface events from {len(interface_collections)} collections")
        return DeviceDataResponse(data=all_data, count=len(all_data))
        
    except Exception as e:
        logger.error(f"Error in get_interface_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching interface data: {str(e)}") 