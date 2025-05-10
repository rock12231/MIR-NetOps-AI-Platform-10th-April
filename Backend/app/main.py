import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import configurations and utility functions first
from app.config import logger as app_logger # Use the app-level logger from config
from app.qdrant_utils import setup_qdrant

# Import services and routers
from app.agent_service import RouterAgent
from app.system_router import router as system_router 
from app.ai_summary import router as ai_summary
from app.chat_router import router as chat_router
from app.dashboard_router import router as dashboard_router

# Initialize FastAPI app
app = FastAPI(title="Network Log Analysis and Chat Agent API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods
    allow_headers=["*"], # Allow all headers
)

# Application startup event
@app.on_event("startup")
async def startup_event():
    app_logger.info("Application startup: Initializing resources...")
    # Initialize Qdrant collections (verify they exist, etc.)
    setup_qdrant()
    
    # Initialize and store RouterAgent in app state
    # This makes it a singleton accessible via request.app.state.router_agent
    app.state.router_agent = RouterAgent()
    app_logger.info("RouterAgent initialized and added to app state.")
    app_logger.info("Application startup complete.")

# Application shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    app_logger.info("Application shutdown: Cleaning up resources...")
    # Add any cleanup logic here if needed (e.g., closing persistent connections)
    app_logger.info("Application shutdown complete.")


# Include routers
app.include_router(system_router) 
app.include_router(ai_summary)
app.include_router(chat_router)
app.include_router(dashboard_router)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the Network Analysis and Chat Agent API!"}

# Main entry point for running the application (e.g., with Uvicorn)
if __name__ == "__main__":
    # This allows running the app directly using `python main.py` from within the /app directory
    # For production, prefer `uvicorn app.main:app --host 0.0.0.0 --port 8001` run from parent of /app
    app_logger.info("Starting Uvicorn server directly from main.py...")
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
    # Note: If running from parent of /app, use "app.main:app"
    # uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True, reload_dirs=["app"])