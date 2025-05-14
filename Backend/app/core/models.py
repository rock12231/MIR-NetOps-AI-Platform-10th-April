from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

# --- Models for Authentication ---
class User(BaseModel):
    """
    User model for authentication and session management.
    
    Attributes:
        username: The user's unique identifier
        email: Optional email address
        disabled: Whether the user account is disabled
    """
    username: str
    email: Optional[str] = None
    disabled: Optional[bool] = False

# --- Models for Network Log Analysis ---
class AnalyzeLogsRequest(BaseModel):
    """
    Request model for analyzing specific log entries.
    
    Allows analyzing logs either by their IDs or by providing the logs directly.
    
    Attributes:
        log_ids: Optional list of log entry IDs to analyze
        logs: Optional list of log entries to analyze
        collection_name: Qdrant collection name to search in (optional)
    """
    log_ids: Optional[List[str]] = []
    logs: Optional[List[Any]] = []
    collection_name: Optional[str] = None

class SummaryRequest(BaseModel):
    """
    Request model for generating a summary of logs from a collection.
    
    Allows filtering logs by various parameters.
    
    Attributes:
        collection_name: Qdrant collection name to summarize
        limit: Maximum number of logs to retrieve
        start_time: Optional Unix timestamp for filtering (start time)
        end_time: Optional Unix timestamp for filtering (end time)
        include_latest: Whether to include the latest log entry
        category: Optional category filter
        event_type: Optional event type filter
        severity: Optional severity filter
        interface: Optional interface filter
    """
    collection_name: str
    limit: int = 20
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    include_latest: Optional[bool] = False
    category: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[str] = None
    interface: Optional[str] = None