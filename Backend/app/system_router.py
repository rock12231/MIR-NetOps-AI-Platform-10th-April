import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Request

from app.config import qdrant, llm # Import initialized clients

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["System"])

@router.get("/health", response_model=Dict)
async def system_health_check(request: Request):
    logger.info("System health check requested.")
    qdrant_ok = False
    llm_ok = False
    try:
        qdrant.get_collections() # Simple check for Qdrant
        qdrant_ok = True
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")

    try:
        llm.complete("Test connection") # Simple check for LLM
        llm_ok = True
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")

    if qdrant_ok and llm_ok:
        return {"status": "healthy", "qdrant_status": "ok", "llm_status": "ok"}
    else:
        details = {
            "qdrant_status": "ok" if qdrant_ok else "error",
            "llm_status": "ok" if llm_ok else "error",
        }
        logger.error(f"System health check failed. Details: {details}")
        raise HTTPException(status_code=503, detail={"status": "unhealthy", **details})