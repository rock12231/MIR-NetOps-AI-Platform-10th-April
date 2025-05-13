from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

# --- Models for Authentication and Agent ---
class User(BaseModel):
    username: str
    email: Optional[str] = None
    disabled: Optional[bool] = False

class ChatCompletionRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., description="List of chat messages")

class ChatCompletionResponse(BaseModel):
    status: str
    response: str
    error: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)

class RouterAgentResponse(BaseModel):
    status: str
    response: str
    error: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)

class RouterQuery(BaseModel):
    query: str = Field(..., description="The query text to analyze")

class AgentResponse(RouterAgentResponse): # Inherits from RouterAgentResponse
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


# --- Models for Network Log Analysis ---
class AnalyzeLogsRequest(BaseModel):
    log_ids: Optional[List[str]] = []
    logs: Optional[List[Any]] = []
    collection_name: Optional[str] # Set default in usage or from qdrant_utils

class SummaryRequest(BaseModel):
    collection_name: str # Set default in usage or from qdrant_utils
    limit: int = 20
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    include_latest: Optional[bool] = False
    category: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[str] = None
    interface: Optional[str] = None

class DashboardRequest(BaseModel):
    collection_name: str # Set default in usage or from qdrant_utils
    limit: int = 1000
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    category: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[str] = None
    interface: Optional[str] = None
    time_threshold_minutes: Optional[int] = 30
    min_transitions: Optional[int] = 3