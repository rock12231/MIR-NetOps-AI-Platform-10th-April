import uuid
import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, HTTPException
from qdrant_client.http import models as rest_models
from qdrant_client.http.models import Filter, FieldCondition, Range

from app.config import qdrant
from app.models import DashboardRequest
from app.qdrant_utils import (
    AVAILABLE_COLLECTIONS,
    DEFAULT_COLLECTION,
    parse_collection_name_backend
)
from .analysis_utils import detect_flapping_interfaces, analyze_interface_stability

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Dashboard"])

@router.post("/dashboard")
async def dashboard_data(request: DashboardRequest):
    collection_name = request.collection_name or DEFAULT_COLLECTION
    limit = request.limit
    start_time = request.start_time
    end_time = request.end_time
    # Filters
    category = request.category
    event_type = request.event_type
    severity = request.severity
    interface = request.interface
    # Flapping detection parameters
    time_threshold_minutes = request.time_threshold_minutes
    min_transitions = request.min_transitions
    
    request_id = str(uuid.uuid4())
    logger.info(f"RID: {request_id} - Dashboard data for '{collection_name}', Limit: {limit}, Start: {start_time}, End: {end_time}, Filters: Cat={category}, Evt={event_type}, Sev={severity}, Iface={interface}, FlapThreshold: {time_threshold_minutes}min, FlapTransitions: {min_transitions}")

    _, device_id_context, location_context, _ = parse_collection_name_backend(collection_name)

    try:
        collection_info = qdrant.get_collection(collection_name=collection_name)
    except Exception as e:
        logger.error(f"RID: {request_id} - Collection '{collection_name}' not found or error: {e}", exc_info=True)
        if collection_name not in AVAILABLE_COLLECTIONS:
             raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' is not in the list of available collections.")
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not accessible in Qdrant: {str(e)}")

    conditions = []
    if start_time: conditions.append(FieldCondition(key="timestamp", range=Range(gte=start_time)))
    if end_time: conditions.append(FieldCondition(key="timestamp", range=Range(lte=end_time)))
    if category: conditions.append(FieldCondition(key="category", match=rest_models.MatchValue(value=category)))
    if event_type: conditions.append(FieldCondition(key="event_type", match=rest_models.MatchValue(value=event_type)))
    if severity: conditions.append(FieldCondition(key="severity", match=rest_models.MatchValue(value=severity)))
    if interface: conditions.append(FieldCondition(key="interface", match=rest_models.MatchValue(value=interface)))
    
    scroll_filter = Filter(must=conditions) if conditions else None

    try:
        # For dashboard, usually want latest data first if not filtered by specific time range fully
        scroll_results, _ = qdrant.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
            order_by=rest_models.OrderBy(key="timestamp", direction="desc")        
            )
        log_entries = [point.payload for point in scroll_results if isinstance(point.payload, dict)]
        logger.info(f"RID: {request_id} - Fetched {len(log_entries)} logs for dashboard.")
    except Exception as e:
        logger.error(f"RID: {request_id} - Error scrolling for dashboard data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving dashboard data from Qdrant: {str(e)}")

    if not log_entries:
        logger.warning(f"RID: {request_id} - No logs found for dashboard with specified filters.")
        return {
            "status": "success", "collection_name": collection_name,
            "points_count": collection_info.points_count,
            "device_context": device_id_context, "location_context": location_context,
            "data": [], "flapping_interfaces": [], "stability_metrics": [],
            "request_time_period": {
                "start": str(datetime.fromtimestamp(start_time)) if start_time else None,
                "end": str(datetime.fromtimestamp(end_time)) if end_time else None
            }
        }
    
    # Perform analyses
    flapping_interfaces_data = detect_flapping_interfaces(
        logs=log_entries,
        time_threshold_minutes=time_threshold_minutes,
        min_transitions=min_transitions
    )
    logger.info(f"RID: {request_id} - Detected {len(flapping_interfaces_data)} flapping interfaces.")

    stability_metrics_data = analyze_interface_stability(logs=log_entries)
    logger.info(f"RID: {request_id} - Calculated stability metrics for {len(stability_metrics_data)} interfaces.")

    return {
        "status": "success",
        "collection_name": collection_name,
        "points_count": collection_info.points_count,
        "device_context": device_id_context,
        "location_context": location_context,
        "retrieved_log_count": len(log_entries),
        "data": log_entries, # The raw logs retrieved
        "flapping_interfaces": flapping_interfaces_data,
        "stability_metrics": stability_metrics_data,
        "request_time_period": {
            "start": str(datetime.fromtimestamp(start_time)) if start_time else None,
            "end": str(datetime.fromtimestamp(end_time)) if end_time else None
        }
    } 