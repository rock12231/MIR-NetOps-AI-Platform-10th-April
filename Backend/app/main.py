# Backend/app/main.py
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import configurations and utility functions
from app.core.config import logger as app_logger
from app.utils.qdrant_utils import setup_qdrant

# Import routers
from app.routers.system_router import router as system_router 
from app.routers.ai_summary_router import router as ai_summary_router
from app.routers.network_overview_router import router as network_overview_router
from app.routers.devices_dashboard_router import router as devices_dashboard_router
from app.routers.interface_monitoring_router import router as interface_monitoring_router

# Initialize FastAPI app
app = FastAPI(
    title="Network Log Analysis API",
    description="API for analyzing network logs and generating summaries",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Application startup event
@app.on_event("startup")
async def startup_event():
    """Initialize resources on application startup"""
    app_logger.info("Application startup: Initializing resources...")
    # Initialize Qdrant collections
    setup_qdrant()
    app_logger.info("Application startup complete.")

# Application shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown"""
    app_logger.info("Application shutdown: Cleaning up resources...")
    # Add any cleanup logic here if needed (e.g., closing persistent connections)
    app_logger.info("Application shutdown complete.")

# Include routers
app.include_router(system_router)
app.include_router(ai_summary_router)
app.include_router(network_overview_router)
app.include_router(devices_dashboard_router)
app.include_router(interface_monitoring_router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint providing basic API information"""
    return {
        "message": "Welcome to the Network Analysis API!",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "health": "/system/health",
            "info": "/system/info",
            "summary": "/api/v1/generate_summary",
            "analyze": "/api/v1/analyze_logs",
            "network": "/api/v1/network/aggregated_data",
            "metadata": "/api/v1/network/metadata",
            "devices": "/api/v1/devices/device_data",
            "interfaces": "/api/v1/devices/interface_data",
            "interface_monitoring": "/api/v1/interfaces/interface_data"
        }
    }

# Main entry point for running the application directly
if __name__ == "__main__":
    app_logger.info("Starting server directly from main.py...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)