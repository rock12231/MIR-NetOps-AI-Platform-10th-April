# Backend/app/routers/network_overview_router.py
import logging
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends
from qdrant_client.http import models
from qdrant_client.models import Filter, FieldCondition, Range, MatchValue
import pandas as pd
from io import StringIO

from app.core.config import qdrant
from app.utils.qdrant_utils import AVAILABLE_COLLECTIONS, parse_collection_name_backend
from app.core.models import NetworkMetadataResponse, AggregatedNetworkDataRequest, AggregatedNetworkDataResponse

# Configure logger
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/network", tags=["Network Overview"])

# Path to metadata file
METADATA_PATH = os.path.join("data", "qdrant_db_metadata.json")

@router.get("/metadata", response_model=NetworkMetadataResponse)
async def get_metadata():
    """
    Get metadata about collections and devices for UI filtering.
    """
    try:
        if os.path.exists(METADATA_PATH):
            with open(METADATA_PATH, 'r') as f:
                metadata = json.load(f)
                return NetworkMetadataResponse(**metadata)
        else:
            logger.warning(f"Metadata file {METADATA_PATH} not found")
            return NetworkMetadataResponse(**get_default_metadata())
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing metadata file: {str(e)}")
        return NetworkMetadataResponse(**get_default_metadata())
    except Exception as e:
        logger.error(f"Error loading metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading metadata: {str(e)}")

def get_default_metadata():
    """
    Get default metadata structure when the metadata file is missing or invalid.
    """
    logger.info("Using default metadata configuration")
    return {
        "collections": AVAILABLE_COLLECTIONS,
        "agw": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": []},
        "dgw": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": []},
        "fw": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": [], "processes": []},
        "vadc": {"devices": [], "locations": [], "categories": [], "event_types": [], "interfaces": []}
    }

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

@router.get("/aggregated_data", response_model=AggregatedNetworkDataResponse)
async def get_aggregated_network_data(
    request: AggregatedNetworkDataRequest = Depends()
):
    """
    Fetch aggregated network data across multiple collections for network-wide analysis.
    """
    try:
        # Get list of collections
        all_collections = await get_collections()
        
        # Filter collections based on device types if specified
        if request.device_types:
            filtered_collections = []
            for col in all_collections:
                for device_type in request.device_types:
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
                # Parse device type and location from collection name
                device_type, device_id, location, _ = parse_collection_name_backend(collection_name)
                
                # Skip if location filtering is active and this location isn't included
                if request.locations and location not in request.locations:
                    continue
                
                # Convert timestamps to seconds
                start_timestamp = int(request.start_time.timestamp())
                end_timestamp = int(request.end_time.timestamp())
                
                # Create filter conditions
                must_conditions = [
                    FieldCondition(
                        key="timestamp",
                        range=Range(
                            gte=start_timestamp,
                            lte=end_timestamp
                        )
                    )
                ]
                
                # Create filter
                search_filter = Filter(must=must_conditions)
                
                # Execute the query
                search_result = qdrant.scroll(
                    collection_name=collection_name,
                    scroll_filter=search_filter,
                    limit=request.limit_per_collection,
                    with_payload=True
                )
                
                # Convert to list of dictionaries
                records = [item.payload for item in search_result[0]]
                
                if records:
                    # Add device type and location if not present
                    for record in records:
                        if 'device_type' not in record:
                            record['device_type'] = device_type
                        if 'location' not in record:
                            record['location'] = location
                        if 'device' not in record:
                            record['device'] = device_id
                    
                    all_data.extend(records)
                    
            except Exception as e:
                logger.error(f"Error fetching data from {collection_name}: {str(e)}")
                continue
        
        # Return data as list of dictionaries
        logger.info(f"Fetched {len(all_data)} records from {len(collections)} collections")
        return AggregatedNetworkDataResponse(data=all_data, count=len(all_data))
    
    except Exception as e:
        logger.error(f"Error in get_aggregated_network_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching aggregated network data: {str(e)}") 