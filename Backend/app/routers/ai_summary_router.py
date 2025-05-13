import uuid
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException
from qdrant_client.http import models as rest_models # Qdrant specific models
from qdrant_client.http.models import Filter, FieldCondition, Range, OrderBy # Qdrant specific models

from app.core.config import qdrant, llm, token_logger
from app.core.models import AnalyzeLogsRequest, SummaryRequest
from app.utils.qdrant_utils import (
    AVAILABLE_COLLECTIONS,
    DEFAULT_COLLECTION,
    parse_collection_name_backend
)
from app.utils.llm_utils import load_prompt_template, clean_and_parse_json, count_tokens
from app.utils.analysis_utils import detect_flapping_interfaces, analyze_interface_stability

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Network Log Analysis"])

# Get LLM provider from environment for token counting and logging
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()


@router.get("/collections")
async def get_collections_endpoint():
    logger.info("Received request for /api/v1/collections")
    try:
        collection_stats = []
        qdrant_collections_info = qdrant.get_collections()
        qdrant_collection_names = {c.name for c in qdrant_collections_info.collections}

        for collection_name in AVAILABLE_COLLECTIONS:
            points_count = 0
            status = "listed_not_found" # Default status if not found in Qdrant's list
            
            try:
                if collection_name in qdrant_collection_names:
                    # Collection exists, get its info
                    info = qdrant.get_collection(collection_name=collection_name)
                    points_count = info.points_count
                    status = "found"
                else:
                    logger.warning(f"Collection '{collection_name}' is listed in AVAILABLE_COLLECTIONS but not present in Qdrant.")
                
                device_type, device_id, location, type_suffix = parse_collection_name_backend(collection_name)
                collection_stats.append({
                    "name": collection_name,
                    "points_count": points_count if status == "found" else 0, # Show 0 if not found, or could be None
                    "status": status,
                    "device_type": device_type,
                    "device_id": device_id,
                    "location": location,
                    "type_suffix": type_suffix
                })
            except Exception as col_info_e: # Catch errors during individual collection processing
                logger.error(f"Error processing collection '{collection_name}': {col_info_e}", exc_info=True)
                device_type, device_id, location, type_suffix = parse_collection_name_backend(collection_name)
                collection_stats.append({
                    "name": collection_name, "points_count": None, "status": "error_retrieving_info",
                    "device_type": device_type, "device_id": device_id, "location": location, "type_suffix": type_suffix
                })
        
        # Sort by points_count (descending), handling None values by treating them as 0 for sorting
        collection_stats.sort(key=lambda x: x.get("points_count", 0) or 0, reverse=True)
        return {"status": "success", "collections": collection_stats}

    except Exception as e:
        logger.error(f"Error fetching collections list from Qdrant: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching collections: {str(e)}")


@router.post("/generate_summary")
async def generate_summary(request: SummaryRequest):
    collection_name = request.collection_name or DEFAULT_COLLECTION
    limit = request.limit
    start_time = request.start_time
    end_time = request.end_time
    include_latest = request.include_latest
    # Filters from request
    category = request.category
    event_type = request.event_type
    severity = request.severity
    interface = request.interface
    
    request_id = str(uuid.uuid4())
    logger.info(f"RID: {request_id} - Summary for '{collection_name}', Limit: {limit}, Start: {start_time}, End: {end_time}, Latest: {include_latest}, Filters: Cat={category}, Evt={event_type}, Sev={severity}, Iface={interface}")

    _, device_id_context, location_context, _ = parse_collection_name_backend(collection_name)

    try:
        collection_info = qdrant.get_collection(collection_name=collection_name)
    except Exception as e:
        logger.error(f"Collection '{collection_name}' not found or error: {e}", exc_info=True)
        if collection_name not in AVAILABLE_COLLECTIONS:
             raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' is not in the list of available collections.")
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not accessible in Qdrant: {str(e)}")

    conditions = []
    if start_time is not None:
        if not isinstance(start_time, int): raise HTTPException(status_code=400, detail="start_time must be int Unix timestamp.")
        conditions.append(FieldCondition(key="timestamp", range=Range(gte=start_time)))
    if end_time is not None:
        if not isinstance(end_time, int): raise HTTPException(status_code=400, detail="end_time must be int Unix timestamp.")
        conditions.append(FieldCondition(key="timestamp", range=Range(lte=end_time)))
    if category: conditions.append(FieldCondition(key="category", match=rest_models.MatchValue(value=category)))
    if event_type: conditions.append(FieldCondition(key="event_type", match=rest_models.MatchValue(value=event_type)))
    if severity: conditions.append(FieldCondition(key="severity", match=rest_models.MatchValue(value=severity)))
    if interface: conditions.append(FieldCondition(key="interface", match=rest_models.MatchValue(value=interface)))
    
    scroll_filter = Filter(must=conditions) if conditions else None
    log_entries_payloads: List[Dict[Any, Any]] = []

    if include_latest:
        try:
            # Fetch logs without ordering
            latest_results, _ = qdrant.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter, # Apply filters to latest as well
                limit=limit,  # Get more logs to ensure we have enough after filtering
                with_payload=True,
                with_vectors=False
            )
            
            if latest_results:
                # Sort by timestamp in memory
                sorted_results = sorted(
                    latest_results,
                    key=lambda x: x.payload.get('timestamp', 0) if isinstance(x.payload, dict) else 0,
                    reverse=True  # Descending order
                )
                # Take the most recent one
                if sorted_results and isinstance(sorted_results[0].payload, dict):
                    log_entries_payloads.append(sorted_results[0].payload)
                    logger.info(f"RID: {request_id} - Fetched latest log entry.")
        except Exception as e:
            logger.error(f"RID: {request_id} - Error fetching latest log: {e}", exc_info=True)
        # Adjust limit if latest was fetched
        limit = max(0, limit - len(log_entries_payloads))

    if limit > 0: # If we still need more logs or didn't ask for latest
        try:
            # Fetch other logs (not necessarily sorted if no order_by is specified for scroll, Qdrant's default order)
            # If a specific order is needed for the "sampled" logs (e.g. random, or also latest), specify order_by
            scroll_results, _ = qdrant.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            fetched_payloads = [point.payload for point in scroll_results if isinstance(point.payload, dict)]
            log_entries_payloads.extend(fetched_payloads)
            logger.info(f"RID: {request_id} - Scrolled {len(fetched_payloads)} additional logs. Total unique after potential merge: {len(log_entries_payloads)}")
        except Exception as e:
            logger.error(f"RID: {request_id} - Error scrolling collection '{collection_name}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error retrieving data from Qdrant: {str(e)}")

    # Deduplicate if 'latest' was fetched and then more were scrolled (rare if filters are specific)
    seen_ids = set()
    unique_log_entries = []
    for log_payload in log_entries_payloads:
        # Assuming logs have a unique ID in their payload, e.g., '_id' or 'log_id'
        # If not, can use hash of content, or rely on Qdrant point ID if available and stable.
        # For this example, let's assume qdrant point ID was part of payload or use a composite key.
        # The original `_qdrant_id` is not in payload by default. `id=point.id`
        # Here, we'll use a simple heuristic or assume a unique field exists.
        # Let's assume `raw_log` + `timestamp` is reasonably unique for deduplication.
        log_unique_key = (log_payload.get("raw_log"), log_payload.get("timestamp"))
        if log_unique_key not in seen_ids:
            seen_ids.add(log_unique_key)
            unique_log_entries.append(log_payload)
    
    log_entries = unique_log_entries # Now using the de-duplicated list

    if not log_entries:
        logger.warning(f"RID: {request_id} - No log entries found for '{collection_name}' with specified filters.")
        # Return a success response with empty analysis
        return {
            "status": "success", "collection_name": collection_name,
            "points_count": collection_info.points_count, "sample_size": 0,
            "device": device_id_context, "location": location_context,
            "input_tokens":0, "output_tokens":0,
            "request_time_period": {
                "start": str(datetime.fromtimestamp(start_time)) if start_time else None,
                "end": str(datetime.fromtimestamp(end_time)) if end_time else None
            },
            "analysis": {"summary": "No log entries found to analyze.", "anomalies": [], "recommendations": []},
            "sampled_logs": []
        }

    prompt_template_str = load_prompt_template()
    # Schema definition should be robust for JSON parsing
    model_schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Concise summary of findings."},
            "normal_patterns": {"type": "array", "items": {"type": "string"}, "description": "Observed normal operational patterns."},
            "anomalies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "log_id": {"type": ["string", "null"], "description": "Identifier of the log entry if available."},
                        "timestamp": {"type": ["string", "number", "null"], "description": "Timestamp of the anomaly."},
                        "device": {"type": ["string", "null"], "description": "Device associated with the anomaly."},
                        "location": {"type": ["string", "null"], "description": "Location of the device."},
                        "category": {"type": ["string", "null"], "description": "Category of the anomalous event."},
                        "description": {"type": "string", "description": "Detailed description of the anomaly."},
                        "severity": {"type": "string", "enum": ["Low", "Medium", "High", "Critical"], "description": "Assessed severity of the anomaly."},
                        "requires_review": {"type": "boolean", "description": "True if immediate review is recommended."},
                        "reasoning": {"type": "string", "description": "Justification for classifying this as an anomaly and its severity."}
                    },
                    "required": ["description", "severity", "requires_review", "reasoning"]
                },
                "description": "List of identified anomalies."
            },
            "recommendations": {"type": "array", "items": {"type": "string"}, "description": "Actionable recommendations."},
            "devices_analyzed": {"type": "array", "items": {"type": "string"}, "description": "List of unique device IDs found in logs."},
            "locations_analyzed": {"type": "array", "items": {"type": "string"}, "description": "List of unique location codes found in logs."},
            "time_period": {
                "type": ["object", "null"],
                "properties": {
                    "start": {"type": ["string", "null"], "description": "Earliest log timestamp in ISO format."},
                    "end": {"type": ["string", "null"], "description": "Latest log timestamp in ISO format."}
                },
                "description": "Time period covered by the analyzed logs."
            }
        },
        "required": ["summary", "normal_patterns", "anomalies", "recommendations", "devices_analyzed", "locations_analyzed"]
    }

    formatted_prompt = prompt_template_str.format(
        log_type=f"network device ({device_id_context} at {location_context})",
        network_prompt=f"Focus on accurately identifying unusual network behavior for collection {collection_name}. Summarize findings based ONLY on the provided logs.",
        model_schema=json.dumps(model_schema, indent=2),
        logs=json.dumps(log_entries, indent=2, default=str) # Ensure datetimes, etc., are serialized
    )

    input_token_count = count_tokens(formatted_prompt, provider=LLM_PROVIDER)
    logger.info(f"RID: {request_id} - Input token count approx: {input_token_count} for provider: {LLM_PROVIDER}")

    try:
        response = llm.complete(formatted_prompt)
        raw_response_text = str(response)
    except Exception as e:
        logger.error(f"RID: {request_id} - LLM API call failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Error communicating with LLM: {str(e)}")

    output_token_count = count_tokens(raw_response_text, provider=LLM_PROVIDER)
    token_logger.info(f"RID: {request_id}, Collection: {collection_name}, Provider: {LLM_PROVIDER}, Logs: {len(log_entries)}, InTokens: {input_token_count}, OutTokens: {output_token_count}")
    logger.debug(f"RID: {request_id} - Raw LLM response:\n{raw_response_text}")

    analysis_json, error_msg = clean_and_parse_json(raw_response_text)
    if error_msg and not analysis_json:
        # If both error_msg is not None and analysis_json is None, then the parsing completely failed
        logger.error(f"RID: {request_id} - Failed to parse LLM JSON response: {error_msg}. Raw response was: {raw_response_text[:500]}...")
        raise HTTPException(status_code=500, detail=f"LLM response parsing error: {error_msg}")
    elif error_msg and analysis_json:
        # If we have both an error_msg and analysis_json, it means we're using a fallback JSON
        logger.warning(f"RID: {request_id} - Using fallback JSON due to parsing issues: {error_msg}")
        # We'll continue with the fallback JSON in this case

    # Augment analysis with context if needed (e.g., time period from request)
    analysis_json['time_period_requested'] = { # Add the requested time for clarity
        "start": str(datetime.fromtimestamp(start_time)) if start_time else None,
        "end": str(datetime.fromtimestamp(end_time)) if end_time else None
    }
    # The LLM should populate 'time_period' based on log data it sees.

    return {
        "status": "success",
        "collection_name": collection_name,
        "points_count": collection_info.points_count,
        "sample_size": len(log_entries),
        "device": device_id_context,
        "location": location_context,
        "input_tokens": input_token_count,
        "output_tokens": output_token_count,
        "analysis": analysis_json,
        "sampled_logs": log_entries, # Return the logs used for analysis
        "request_time_period": analysis_json['time_period_requested'] # For frontend to display easily
    }


@router.post("/analyze_logs")
async def analyze_logs_detailed(request: AnalyzeLogsRequest):
    log_ids = request.log_ids or []
    custom_logs = request.logs or [] # Logs provided directly in the request
    collection_name = request.collection_name or DEFAULT_COLLECTION
    request_id = str(uuid.uuid4())
    logger.info(f"RID: {request_id} - Analyze logs for '{collection_name}', IDs: {len(log_ids)}, Custom: {len(custom_logs)}")

    _, device_id_context, location_context, _ = parse_collection_name_backend(collection_name)

    if not log_ids and not custom_logs:
        raise HTTPException(status_code=400, detail="Either log_ids or logs must be provided.")

    log_entries: List[Dict[Any, Any]] = []
    if log_ids:
        try:
            # Ensure collection exists before retrieving
            qdrant.get_collection(collection_name=collection_name) 
            # Retrieve points by ID
            points = qdrant.retrieve(
                collection_name=collection_name, 
                ids=log_ids, 
                with_payload=True, 
                with_vectors=False # No need for vectors for analysis
            )
            retrieved_payloads = [p.payload for p in points if isinstance(p.payload, dict)]
            log_entries.extend(retrieved_payloads)
            logger.info(f"RID: {request_id} - Retrieved {len(retrieved_payloads)} logs by ID from '{collection_name}'.")
            if len(retrieved_payloads) < len(log_ids):
                 logger.warning(f"RID: {request_id} - Could not find all requested log IDs. Found {len(retrieved_payloads)} of {len(log_ids)}.")
        except Exception as e:
            logger.error(f"RID: {request_id} - Error retrieving logs by ID from '{collection_name}': {e}", exc_info=True)
            # Decide if this is a critical failure or if we can proceed with custom_logs
            if not custom_logs: # If no custom logs to fall back on, then it's an error
                raise HTTPException(status_code=500, detail=f"Error retrieving logs by ID: {str(e)}")

    if custom_logs:
        validated_custom_logs = [log for log in custom_logs if isinstance(log, dict)]
        log_entries.extend(validated_custom_logs)
        logger.info(f"RID: {request_id} - Added {len(validated_custom_logs)} custom logs for analysis.")
        if len(validated_custom_logs) < len(custom_logs):
            logger.warning(f"RID: {request_id} - Some provided custom logs were not valid dictionaries and were ignored.")


    if not log_entries:
        raise HTTPException(status_code=404, detail="No valid logs found or provided for analysis.")

    # Deduplicate, similar to generate_summary if needed, though less likely here
    # For this endpoint, assume logs are distinct or duplication is acceptable

    prompt_template_str = load_prompt_template()
    # Using the same schema as generate_summary for consistency in LLM output
    model_schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"}, "normal_patterns": {"type": "array", "items": {"type": "string"}},
            "anomalies": { "type": "array", "items": { "type": "object", "properties": {
                            "log_id": {"type": ["string", "null"]}, "timestamp": {"type": ["string", "number", "null"]},
                            "device": {"type": ["string", "null"]}, "location": {"type": ["string", "null"]},
                            "category": {"type": ["string", "null"]}, "description": {"type": "string"},
                            "severity": {"type": "string", "enum": ["Low", "Medium", "High", "Critical"]},
                            "requires_review": {"type": "boolean"}, "reasoning": {"type": "string"}
                        }, "required": ["description", "severity", "requires_review", "reasoning"]}},
            "recommendations": {"type": "array", "items": {"type": "string"}},
            "devices_analyzed": {"type": "array", "items": {"type": "string"}},
            "locations_analyzed": {"type": "array", "items": {"type": "string"}},
            "time_period": {"type": ["object", "null"], "properties": {"start": {"type": ["string", "null"]}, "end": {"type": ["string", "null"]}}}
        },
        "required": ["summary", "normal_patterns", "anomalies", "recommendations", "devices_analyzed", "locations_analyzed"]
    }

    formatted_prompt = prompt_template_str.format(
        log_type=f"specific network device logs ({device_id_context} at {location_context})",
        network_prompt="Provide a detailed analysis of these *specific* log entries. Focus on inter-log correlations if multiple logs are provided.",
        model_schema=json.dumps(model_schema, indent=2),
        logs=json.dumps(log_entries, indent=2, default=str)
    )

    input_token_count = count_tokens(formatted_prompt, provider=LLM_PROVIDER)
    logger.info(f"RID: {request_id} - Input token count for detailed analysis: {input_token_count} for provider: {LLM_PROVIDER}")

    try:
        response = llm.complete(formatted_prompt)
        raw_response_text = str(response)
    except Exception as e:
        logger.error(f"RID: {request_id} - LLM API call failed for detailed analysis: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Error communicating with LLM: {str(e)}")

    output_token_count = count_tokens(raw_response_text, provider=LLM_PROVIDER)
    token_logger.info(f"RID: {request_id}, Collection: {collection_name} (AnalyzeLogs), Provider: {LLM_PROVIDER}, Logs: {len(log_entries)}, InTokens: {input_token_count}, OutTokens: {output_token_count}")
    logger.debug(f"RID: {request_id} - Raw LLM response (detailed analysis):\n{raw_response_text}")

    analysis_json, error_msg = clean_and_parse_json(raw_response_text)
    if error_msg and not analysis_json:
        # If both error_msg is not None and analysis_json is None, then the parsing completely failed
        logger.error(f"RID: {request_id} - Failed to parse LLM JSON response for detailed analysis: {error_msg}. Raw: {raw_response_text[:500]}...")
        raise HTTPException(status_code=500, detail=f"LLM response parsing error for detailed analysis: {error_msg}")
    elif error_msg and analysis_json:
        # If we have both an error_msg and analysis_json, it means we're using a fallback JSON
        logger.warning(f"RID: {request_id} - Using fallback JSON for detailed analysis due to parsing issues: {error_msg}")
        # We'll continue with the fallback JSON in this case
    
    # The LLM should populate 'time_period' based on log data it sees.

    return {
        "status": "success",
        "collection_name": collection_name,
        "device_context": device_id_context, # Device/location from collection name
        "location_context": location_context,
        "input_tokens": input_token_count,
        "output_tokens": output_token_count,
        "analysis": analysis_json,
        "analyzed_log_count": len(log_entries)
        # Optionally return log_entries if they were retrieved by ID and client doesn't have them
        # "analyzed_logs": log_entries 
    }