"""
ComfyUI Docker Manager - FastAPI Application
Main entry point for the backend server.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .config import config_manager, get_config
from .docker_manager import docker_manager
from .idle_monitor import idle_monitor
from .proxy import proxy_handler
from .routes import api, websocket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("ComfyUI Docker Manager starting up...")

    # Load configuration
    config = config_manager.load()
    logger.info(f"Configuration loaded. Container: {config.container_name}")

    # Check Docker connection
    try:
        status = docker_manager.get_status()
        logger.info(f"Docker connection OK. Container status: {status['state']}")
    except Exception as e:
        logger.error(f"Docker connection failed: {e}")

    # Start idle monitor
    idle_monitor.start()
    logger.info("Idle monitor started")

    yield

    # Shutdown
    logger.info("ComfyUI Docker Manager shutting down...")
    idle_monitor.stop()


# Create FastAPI app
app = FastAPI(
    title="ComfyUI Docker Manager",
    description="Automatically manage ComfyUI Docker container based on demand",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api.router)
app.include_router(websocket.router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "comfyui-manager"}


# Serve frontend static files if they exist
# In Docker: /app/static, in development: ../static relative to this file
STATIC_DIR = os.environ.get("STATIC_DIR", os.path.join(os.path.dirname(__file__), "..", "static"))
if not os.path.isabs(STATIC_DIR):
    STATIC_DIR = os.path.abspath(STATIC_DIR)

logger.info(f"Static directory: {STATIC_DIR}, exists: {os.path.exists(STATIC_DIR)}")

if os.path.exists(STATIC_DIR):
    # Mount manager's static assets at /manager-assets to avoid conflict with ComfyUI
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/manager-assets", StaticFiles(directory=assets_dir), name="manager-assets")


# Proxy routes for ComfyUI - these need to be defined before the catch-all frontend route
# Proxy all common ComfyUI paths
@app.api_route("/comfyui/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_comfyui(request: Request, path: str):
    """Proxy requests to ComfyUI."""
    return await proxy_handler.handle_request(request)


@app.api_route("/comfyui", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_comfyui_root(request: Request):
    """Proxy requests to ComfyUI root."""
    return await proxy_handler.handle_request(request)


# Manager frontend routes
@app.get("/")
async def serve_frontend():
    """Serve the manager frontend SPA."""
    if os.path.exists(STATIC_DIR):
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            # Read and modify the index.html to use /manager-assets instead of /assets
            with open(index_path, 'r') as f:
                content = f.read()
            content = content.replace('"/assets/', '"/manager-assets/')
            content = content.replace("'/assets/", "'/manager-assets/")
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=content)
    return {
        "service": "ComfyUI Docker Manager",
        "version": "1.0.0",
        "api_docs": "/docs",
        "status": "Frontend not built. Run 'npm run build' in frontend directory."
    }


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.manager_port,
        reload=True
    )
