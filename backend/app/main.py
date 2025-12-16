"""
ComfyUI Docker Manager - FastAPI Application
Main entry point for the backend server.

Architecture:
- ComfyUI is proxied at the ROOT (/) for full compatibility
- Manager dashboard is served at /manager
- API endpoints are at /api
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API and WebSocket routers
app.include_router(api.router)
app.include_router(websocket.router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "comfyui-manager"}


# =============================================================================
# MANAGER DASHBOARD - Served at /manager
# =============================================================================

STATIC_DIR = os.environ.get("STATIC_DIR", os.path.join(os.path.dirname(__file__), "..", "static"))
if not os.path.isabs(STATIC_DIR):
    STATIC_DIR = os.path.abspath(STATIC_DIR)

logger.info(f"Static directory: {STATIC_DIR}, exists: {os.path.exists(STATIC_DIR)}")

# Mount manager static assets - Vite builds with base: '/manager/' so assets are at /manager/assets/
if os.path.exists(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/manager/assets", StaticFiles(directory=assets_dir), name="manager-assets")


@app.get("/manager")
@app.get("/manager/")
async def serve_manager():
    """Serve the manager dashboard."""
    if os.path.exists(STATIC_DIR):
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    return HTMLResponse(
        content="<h1>Manager frontend not built</h1><p>Run 'npm run build' in frontend directory.</p>",
        status_code=500
    )


# =============================================================================
# COMFYUI PROXY - Served at ROOT (/) for full compatibility
# All non-manager, non-api routes go to ComfyUI
# =============================================================================

# Catch-all route - MUST be last
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_all(request: Request, path: str):
    """Proxy all other requests to ComfyUI."""
    # Don't proxy manager, api, ws, or health routes
    if path.startswith(("manager", "api", "ws", "health", "docs", "openapi.json", "redoc")):
        return None
    return await proxy_handler.handle_request(request)


@app.get("/")
async def proxy_root(request: Request):
    """Proxy root to ComfyUI or show manager link."""
    return await proxy_handler.handle_request(request)


if __name__ == "__main__":
    import uvicorn
    config = get_config()
    uvicorn.run("app.main:app", host="0.0.0.0", port=config.manager_port, reload=True)
