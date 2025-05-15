# Backend/app/core/models.py
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
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
        model_provider: Optional model provider for analysis
    """
    collection_name: str
    log_ids: Optional[List[str]] = None
    logs: Optional[List[Dict[str, Any]]] = None
    model_provider: Optional[str] = None

# --- Models for Summary Generation ---
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
        model_provider: Optional model provider for summary generation
    """
    collection_name: Optional[str] = None
    limit: int = Field(default=30, ge=1, le=100, description="Maximum number of logs to analyze")
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    include_latest: bool = False
    category: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[str] = None
    interface: Optional[str] = None
    model_provider: Optional[str] = None

# --- Models for System Status ---
class SystemHealthResponse(BaseModel):
    """
    Response model for system health check endpoint.
    """
    status: str = Field(description="Overall system health status (healthy or unhealthy)")
    qdrant_status: str = Field(description="Status of Qdrant vector database")
    llm_status: str = Field(description="Status of LLM service")

class CollectionInfo(BaseModel):
    """
    Information about a collection in Qdrant.
    """
    name: str = Field(description="Collection name")
    vectors_count: Optional[int] = Field(None, description="Number of vectors in collection")
    points_count: Optional[int] = Field(None, description="Number of points in collection")
    status: str = Field(description="Collection status")

class LLMInfo(BaseModel):
    """
    Information about the LLM service.
    """
    model_name: str = Field(description="Name of the LLM model")
    provider: str = Field(description="Provider of the LLM model")

class SystemInfoResponse(BaseModel):
    """
    Response model for system information endpoint.
    """
    version: str = Field(description="API version")
    qdrant: Dict[str, Any] = Field(description="Information about Qdrant")
    llm: LLMInfo = Field(description="Information about the LLM service")

# --- Models for Network Overview ---
class NetworkMetadataResponse(BaseModel):
    """
    Response model for network metadata.
    """
    collections: List[str] = Field(default_factory=list, description="Available collections")
    agw: Dict[str, List[str]] = Field(default_factory=dict, description="AGW device metadata")
    dgw: Dict[str, List[str]] = Field(default_factory=dict, description="DGW device metadata")
    fw: Dict[str, List[str]] = Field(default_factory=dict, description="Firewall device metadata")
    vadc: Dict[str, List[str]] = Field(default_factory=dict, description="VADC device metadata")

class AggregatedNetworkDataRequest(BaseModel):
    """
    Request model for aggregated network data.
    """
    start_time: datetime = Field(description="Start time for filtering")
    end_time: datetime = Field(description="End time for filtering")
    device_types: Optional[List[str]] = Field(None, description="List of device types to include")
    locations: Optional[List[str]] = Field(None, description="List of locations to include")
    limit_per_collection: int = Field(200, description="Limit records per collection")

class AggregatedNetworkDataResponse(BaseModel):
    """
    Response model for aggregated network data.
    """
    data: List[Dict[str, Any]] = Field(description="Network event data")
    count: int = Field(description="Number of events returned")

# --- Models for Devices Dashboard ---
class DeviceDataRequest(BaseModel):
    """
    Request model for device data.
    """
    collection_name: str = Field(description="Name of the collection to query")
    start_time: datetime = Field(description="Start time for filtering")
    end_time: datetime = Field(description="End time for filtering")
    device: Optional[str] = Field(None, description="Filter by device name")
    location: Optional[str] = Field(None, description="Filter by location")
    category: Optional[str] = Field(None, description="Filter by event category")
    event_type: Optional[str] = Field(None, description="Filter by event type")
    severity: Optional[str] = Field(None, description="Filter by severity")
    interface: Optional[str] = Field(None, description="Filter by interface")
    limit: int = Field(1000, description="Maximum number of records to return")

class InterfaceDataRequest(BaseModel):
    """
    Request model for interface data.
    """
    start_time: datetime = Field(description="Start time for filtering")
    end_time: datetime = Field(description="End time for filtering")
    device_type: Optional[str] = Field(None, description="Filter by device type (e.g., agw)")
    total_limit: int = Field(5000, description="Maximum total records")

class DeviceDataResponse(BaseModel):
    """
    Response model for device data.
    """
    data: List[Dict[str, Any]] = Field(description="Device event data")
    count: int = Field(description="Number of events returned")
    message: Optional[str] = Field(None, description="Optional message")

# --- Models for Interface Monitoring ---
class InterfaceMonitoringDataRequest(BaseModel):
    """
    Request model for interface monitoring data.
    """
    start_time: datetime = Field(description="Start time for filtering")
    end_time: datetime = Field(description="End time for filtering")
    device: Optional[str] = Field(None, description="Filter by device name")
    location: Optional[str] = Field(None, description="Filter by location")
    interface: Optional[str] = Field(None, description="Filter by interface name")
    total_limit: int = Field(10000, description="Maximum total records to return")

class FlappingDetectionRequest(BaseModel):
    """
    Request model for flapping interface detection.
    """
    start_time: datetime = Field(description="Start time for filtering")
    end_time: datetime = Field(description="End time for filtering")
    device: Optional[str] = Field(None, description="Filter by device name")
    location: Optional[str] = Field(None, description="Filter by location")
    interface: Optional[str] = Field(None, description="Filter by interface name")
    time_threshold_minutes: int = Field(30, description="Maximum time between state changes to be considered flapping")
    min_transitions: int = Field(3, description="Minimum number of state transitions required")

class StabilityAnalysisRequest(BaseModel):
    """
    Request model for interface stability analysis.
    """
    start_time: datetime = Field(description="Start time for filtering")
    end_time: datetime = Field(description="End time for filtering")
    device: Optional[str] = Field(None, description="Filter by device name")
    location: Optional[str] = Field(None, description="Filter by location")
    interface: Optional[str] = Field(None, description="Filter by interface name")
    time_window_hours: int = Field(24, description="Time window for analysis in hours")

class EventCategorizationRequest(BaseModel):
    """
    Request model for interface event categorization.
    """
    start_time: datetime = Field(description="Start time for filtering")
    end_time: datetime = Field(description="End time for filtering")
    device: Optional[str] = Field(None, description="Filter by device name")
    location: Optional[str] = Field(None, description="Filter by location")
    interface: Optional[str] = Field(None, description="Filter by interface name")

class InterfaceDataResponse(BaseModel):
    """
    Response model for interface data.
    """
    data: List[Dict[str, Any]] = Field(description="Interface data")
    count: int = Field(description="Number of records")
    message: Optional[str] = Field(None, description="Optional message")