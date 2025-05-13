import uuid
import logging # Standard logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Request, HTTPException
from loguru import logger as loguru_logger # Specific logger from original for this router

from app.core.models import (
    RouterQuery, AgentResponse, ChatCompletionRequest, 
    ChatCompletionResponse, User
)
from app.core.auth import get_current_active_user
from app.services.agent_service import RouterAgent # The agent implementation

# Standard logger for general messages in this module
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat Agent"])

# Helper to get or create a session ID
# Uses loguru_logger as per original file's agent_router section
def get_session_id(http_request: Request, current_user: Optional[User] = None) -> str:
    # Try to get session from Authorization header (if used as session token)
    # Or, generate a new one if not present.
    # This logic might need to align with actual session management strategy (e.g., cookies, custom headers)
    
    auth_header = http_request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header

    username = current_user.username if current_user else "anonymous_chat_user"

    if token and len(token) > 10: # Assuming a reasonable token length
        loguru_logger.info(f"Using token-based session for user {username}: {token[:10]}...")
        return token # Use the provided token as session_id
    else:
        # If no token or too short, generate a new UUID for session_id
        # This part might conflict if Authorization is strictly for auth, not session.
        # Consider a dedicated session header or mechanism.
        new_session_id = str(uuid.uuid4())
        loguru_logger.warning(f"No suitable token for session ID for user {username}. Generated new session: {new_session_id[:10]}...")
        return new_session_id


# Dependency to get the agent instance (from app state)
async def get_router_agent(request: Request) -> RouterAgent:
    if not hasattr(request.app.state, 'router_agent') or request.app.state.router_agent is None:
        logger.error("RouterAgent not found in app.state. It should be initialized in main.py.")
        raise HTTPException(status_code=500, detail="Chat agent service not available.")
    return request.app.state.router_agent


@router.post("/query", response_model=AgentResponse)
async def query_agent(
    query: RouterQuery,
    request: Request, # FastAPI Request object
    current_user: User = Depends(get_current_active_user),
    agent: RouterAgent = Depends(get_router_agent)
):
    session_id = get_session_id(request, current_user)
    loguru_logger.info(f"User '{current_user.username}' (Session: {session_id[:10]}) querying agent: '{query.query[:50]}...'")
    try:
        agent_response = await agent.query(query.query, session_id)
        # Augment metadata
        agent_response.metadata.update({
            "queried_by": current_user.username,
            "query_time_utc": datetime.utcnow().isoformat(),
            "session_id_short": session_id[:10] + "..." # For display, don't log full session ID if sensitive
        })
        return agent_response
    except Exception as e:
        loguru_logger.error(f"Query processing failed for user '{current_user.username}', session {session_id[:10]}: {str(e)}", exc_info=True)
        return AgentResponse( # Ensure it's AgentResponse model
            status="error",
            response="Failed to process query due to an internal error.",
            error=str(e),
            metadata={
                "queried_by": current_user.username,
                "query_time_utc": datetime.utcnow().isoformat(),
                "session_id_short": session_id[:10] + "..."
            }
        )

@router.post("/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    chat_request: ChatCompletionRequest, # Renamed from 'request' to avoid conflict
    http_request: Request, # FastAPI Request object
    current_user: User = Depends(get_current_active_user), # Assuming completions also need auth
    agent: RouterAgent = Depends(get_router_agent)
):
    session_id = get_session_id(http_request, current_user)
    loguru_logger.info(f"User '{current_user.username}' (Session: {session_id[:10]}) requesting chat completion. Messages: {len(chat_request.messages)}")
    
    # Basic validation of messages
    if not chat_request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty.")
    for msg in chat_request.messages:
        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
            raise HTTPException(status_code=400, detail="Each message must be a dict with 'role' and 'content'.")

    try:
        completion_response = await agent.chat_openai(chat_request.messages, session_id)
        completion_response.metadata.update({
            "completed_by": current_user.username,
            "completion_time_utc": datetime.utcnow().isoformat(),
            "session_id_short": session_id[:10] + "..."
        })
        return completion_response
    except Exception as e:
        loguru_logger.error(f"Chat completion failed for user '{current_user.username}', session {session_id[:10]}: {str(e)}", exc_info=True)
        return ChatCompletionResponse(
            status="error",
            response="Failed to get chat completion due to an internal error.",
            error=str(e),
            metadata={
                "completed_by": current_user.username,
                "completion_time_utc": datetime.utcnow().isoformat(),
                "session_id_short": session_id[:10] + "..."
            }
        )


@router.post("/reset", response_model=Dict)
async def reset_conversation(
    request: Request, # FastAPI Request object
    current_user: User = Depends(get_current_active_user),
    agent: RouterAgent = Depends(get_router_agent)
):
    session_id = get_session_id(request, current_user) # Get existing or new session_id
    loguru_logger.info(f"User '{current_user.username}' requesting conversation reset for session: {session_id[:10]}...")
    await agent.reset_conversation(session_id)
    return {
        "status": "success",
        "message": "Conversation history reset successfully.",
        "session_id_short": session_id[:10] + "...",
        "reset_by": current_user.username,
        "reset_time_utc": datetime.utcnow().isoformat()
    }

@router.get("/health", response_model=Dict)
async def check_agent_health(
    request: Request, # FastAPI Request object
    current_user: User = Depends(get_current_active_user),
    agent: RouterAgent = Depends(get_router_agent)
):
    loguru_logger.info(f"User '{current_user.username}' checking agent health.")
    try:
        health_status = await agent.health_check()
        health_status["checked_by"] = current_user.username
        health_status["check_time_utc"] = datetime.utcnow().isoformat()
        return health_status
    except Exception as e:
        loguru_logger.error(f"Agent health check failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Health check process failed: {str(e)}",
            "checked_by": current_user.username,
            "check_time_utc": datetime.utcnow().isoformat()
        }

@router.get("/status", response_model=Dict)
async def get_agent_status(
    request: Request, # FastAPI Request object
    current_user: User = Depends(get_current_active_user),
    agent: RouterAgent = Depends(get_router_agent)
):
    loguru_logger.info(f"User '{current_user.username}' requesting agent status.")
    try:
        health_status = await agent.health_check() # Re-use health check for part of status
        tools_info = [
            {"name": tool.metadata.name, "description": tool.metadata.description}
            for tool in agent.tools
        ]
        active_sessions = agent.session_manager.get_active_sessions_count()
        
        return {
            "status": "success", # Overall status of this endpoint call
            "agent_health": health_status,
            "tools_available": tools_info,
            "active_sessions_count": active_sessions,
            "llm_configuration": {
                "model_name": agent.settings.LLM_MODEL,
                "temperature": agent.settings.LLM_TEMPERATURE,
                "max_tokens": agent.settings.MAX_TOKENS
            },
            "checked_by": current_user.username,
            "status_time_utc": datetime.utcnow().isoformat()
        }
    except Exception as e:
        loguru_logger.error(f"Agent status check failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Status check process failed: {str(e)}",
            "checked_by": current_user.username,
            "status_time_utc": datetime.utcnow().isoformat()
        }