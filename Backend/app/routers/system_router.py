# Backend/app/routers/system_router.py
import logging
from typing import Dict
from fastapi import APIRouter, HTTPException

from app.core.config import qdrant, llm
from app.core.models import SystemHealthResponse, SystemInfoResponse, CollectionInfo, LLMInfo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["System"])

@router.get("/health", response_model=SystemHealthResponse)
async def system_health_check():
    """
    Health check endpoint to verify system components are operational.
    Returns status of Qdrant and LLM services.
    """
    logger.info("System health check requested")
    qdrant_ok = False
    llm_ok = False
    
    # Check Qdrant connection
    try:
        qdrant.get_collections()
        qdrant_ok = True
        logger.info("Qdrant health check: OK")
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")

    # Check LLM connection
    try:
        llm["test_connection"]()
        llm_ok = True
        logger.info("LLM health check: OK")
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")

    # Return appropriate response
    if qdrant_ok and llm_ok:
        return SystemHealthResponse(
            status="healthy", 
            qdrant_status="ok", 
            llm_status="ok"
        )
    else:
        details = SystemHealthResponse(
            status="unhealthy",
            qdrant_status="ok" if qdrant_ok else "error",
            llm_status="ok" if llm_ok else "error",
        )
        logger.warning(f"System health check failed. Details: {details}")
        raise HTTPException(status_code=503, detail=details.dict())

@router.get("/info", response_model=SystemInfoResponse)
async def system_info():
    """
    Returns basic information about the system configuration.
    """
    try:
        # Get info about Qdrant collections
        collections_info = []
        try:
            collections = qdrant.get_collections().collections
            for collection in collections:
                info = qdrant.get_collection(collection_name=collection.name)
                collections_info.append(CollectionInfo(
                    name=collection.name,
                    vectors_count=info.vectors_count,
                    points_count=info.points_count,
                    status="available"
                ))
        except Exception as e:
            logger.error(f"Failed to get collections info: {e}")
            
        # Get LLM info from the wrapper
        llm_info = LLMInfo(
            model_name=llm.get("model_name", "unknown"),
            provider=llm.get("provider", "unknown")
        )
            
        return SystemInfoResponse(
            version="1.0.0",
            qdrant={
                "collections": collections_info,
                "status": "available"
            },
            llm=llm_info
        )
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving system information: {str(e)}")