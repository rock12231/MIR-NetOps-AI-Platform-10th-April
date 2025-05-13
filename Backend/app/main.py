import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import configurations and utility functions first
from app.core.config import logger as app_logger # Use the app-level logger from config
from app.utils.qdrant_utils import setup_qdrant

# Import services and routers
from app.services.agent_service import RouterAgent
from app.routers.system_router import router as system_router 
from app.routers.ai_summary_router import router as ai_summary_router
from app.routers.chat_router import router as chat_router
from app.routers.dashboard_router import router as dashboard_router

# Initialize FastAPI app
app = FastAPI(title="Network Log Analysis and Chat Agent API")

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
app.include_router(ai_summary_router) # Use the consistent imported name
app.include_router(chat_router)
app.include_router(dashboard_router)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the Network Analysis and Chat Agent API!"}

# Main entry point for running the application (e.g., with Uvicorn)
if __name__ == "__main__":
    # This allows running the app directly using `python app/main.py` from project root
    # For production, prefer `uvicorn app.main:app --host 0.0.0.0 --port 8001` run from project root
    app_logger.info("Starting Uvicorn server directly from main.py...")
    # When running with `python app/main.py`, the module is `main` not `app.main`
    # However, for consistency with Docker CMD and standard uvicorn usage,
    # it's better to rely on `uvicorn app.main:app` from the project root.
    # The Docker CMD is `uvicorn app.main:app`, which is correct.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True, reload_dirs=["app"])