"""
REST API endpoints for the manager.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..docker_manager import docker_manager
from ..comfyui_client import comfyui_client
from ..idle_monitor import idle_monitor
from ..config import config_manager, get_config

router = APIRouter(prefix="/api", tags=["api"])


class ConfigUpdate(BaseModel):
    """Configuration update request."""
    idle_timeout_minutes: Optional[int] = None
    poll_interval_seconds: Optional[int] = None
    auto_start_enabled: Optional[bool] = None
    container_name: Optional[str] = None


class StatusResponse(BaseModel):
    """Combined status response."""
    container: dict
    queue: dict
    idle: dict
    config: dict


@router.get("/status")
async def get_status() -> StatusResponse:
    """Get complete system status."""
    # Get container status
    container_status = docker_manager.get_status()

    # Get queue status (may fail if container is stopped)
    queue_status = await comfyui_client.get_queue_status()

    # Get idle info
    idle_info = idle_monitor.get_idle_info()

    # Get config
    config = get_config()

    return StatusResponse(
        container=container_status,
        queue=queue_status.to_dict(),
        idle=idle_info,
        config={
            "idle_timeout_minutes": config.idle_timeout_minutes,
            "poll_interval_seconds": config.poll_interval_seconds,
            "auto_start_enabled": config.auto_start_enabled,
            "container_name": config.container_name,
            "comfyui_url": config.comfyui_browser_url,
        }
    )


@router.post("/start")
async def start_container():
    """Manually start the ComfyUI container."""
    result = await docker_manager.start_container()

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    # Update activity on manual start
    comfyui_client.update_activity()

    return result


@router.post("/stop")
async def stop_container():
    """Manually stop the ComfyUI container."""
    result = await docker_manager.stop_container()

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.get("/config")
async def get_configuration():
    """Get current configuration."""
    config = get_config()
    return {
        "idle_timeout_minutes": config.idle_timeout_minutes,
        "poll_interval_seconds": config.poll_interval_seconds,
        "auto_start_enabled": config.auto_start_enabled,
        "container_name": config.container_name,
        "startup_timeout_seconds": config.startup_timeout_seconds,
        "comfyui_port": config.comfyui_port,
    }


@router.put("/config")
async def update_configuration(update: ConfigUpdate):
    """Update configuration."""
    updates = update.model_dump(exclude_none=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No configuration updates provided")

    # Validate values
    if "idle_timeout_minutes" in updates:
        if updates["idle_timeout_minutes"] < 1:
            raise HTTPException(status_code=400, detail="Idle timeout must be at least 1 minute")
        if updates["idle_timeout_minutes"] > 1440:  # 24 hours
            raise HTTPException(status_code=400, detail="Idle timeout cannot exceed 24 hours")

    if "poll_interval_seconds" in updates:
        if updates["poll_interval_seconds"] < 10:
            raise HTTPException(status_code=400, detail="Poll interval must be at least 10 seconds")
        if updates["poll_interval_seconds"] > 300:
            raise HTTPException(status_code=400, detail="Poll interval cannot exceed 5 minutes")

    # Apply updates
    config = config_manager.update(**updates)

    return {
        "success": True,
        "message": "Configuration updated",
        "config": {
            "idle_timeout_minutes": config.idle_timeout_minutes,
            "poll_interval_seconds": config.poll_interval_seconds,
            "auto_start_enabled": config.auto_start_enabled,
            "container_name": config.container_name,
        }
    }


@router.get("/logs")
async def get_logs(tail: int = 100):
    """Get recent container logs."""
    if tail < 1:
        tail = 1
    if tail > 1000:
        tail = 1000

    logs = docker_manager.get_logs(tail=tail)
    return {"logs": logs}


@router.get("/activity")
async def get_activity_log(limit: int = 50):
    """Get recent activity log from the idle monitor."""
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100

    events = idle_monitor.get_activity_log(limit=limit)
    return {"events": events}


@router.post("/reset-idle")
async def reset_idle_timer():
    """Manually reset the idle timer."""
    comfyui_client.update_activity()
    return {
        "success": True,
        "message": "Idle timer reset",
        "idle": idle_monitor.get_idle_info()
    }
