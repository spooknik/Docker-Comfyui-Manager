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


# Proxy routes - catch all requests to /comfyui/*
@app.api_route("/comfyui/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_comfyui(request: Request, path: str):
    """Proxy requests to ComfyUI."""
    return await proxy_handler.handle_request(request)


@app.api_route("/comfyui", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_comfyui_root(request: Request):
    """Proxy requests to ComfyUI root."""
    return await proxy_handler.handle_request(request)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "comfyui-manager"}


# Serve frontend static files if they exist
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static")

if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        """Serve the frontend SPA."""
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str):
        """Serve frontend for all non-API routes."""
        # Don't intercept API, WebSocket, or comfyui proxy routes
        if path.startswith(("api/", "ws", "comfyui", "health")):
            return None

        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)

        return {"error": "Not found"}
else:
    @app.get("/")
    async def root():
        """Root endpoint when no frontend is built."""
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
