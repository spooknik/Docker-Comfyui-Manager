"""
WebSocket handler for real-time updates.
"""

import asyncio
import logging
from typing import Set
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..docker_manager import docker_manager
from ..comfyui_client import comfyui_client
from ..idle_monitor import idle_monitor
from ..config import get_config

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._broadcast_task: asyncio.Task = None

    async def connect(self, websocket: WebSocket):
        """Accept and track a new connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

        # Start broadcast task if not running
        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())

    def disconnect(self, websocket: WebSocket):
        """Remove a connection."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        if not self.active_connections:
            return

        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        self.active_connections -= disconnected

    async def _broadcast_loop(self):
        """Periodically broadcast status updates to all clients."""
        while self.active_connections:
            try:
                # Build status update
                container_status = docker_manager.get_status()
                queue_status = await comfyui_client.get_queue_status()
                idle_info = idle_monitor.get_idle_info()
                config = get_config()

                message = {
                    "type": "status_update",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "container": container_status,
                        "queue": queue_status.to_dict(),
                        "idle": idle_info,
                        "config": {
                            "idle_timeout_minutes": config.idle_timeout_minutes,
                            "auto_start_enabled": config.auto_start_enabled,
                            "comfyui_url": config.comfyui_browser_url,
                        }
                    }
                }

                await self.broadcast(message)

            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")

            # Wait before next update
            await asyncio.sleep(2)

        logger.info("Broadcast loop stopped - no active connections")


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)

    try:
        # Send initial status
        container_status = docker_manager.get_status()
        queue_status = await comfyui_client.get_queue_status()
        idle_info = idle_monitor.get_idle_info()
        config = get_config()

        await websocket.send_json({
            "type": "initial_status",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "container": container_status,
                "queue": queue_status.to_dict(),
                "idle": idle_info,
                "config": {
                    "idle_timeout_minutes": config.idle_timeout_minutes,
                    "auto_start_enabled": config.auto_start_enabled,
                    "comfyui_url": config.comfyui_browser_url,
                }
            }
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()

                # Handle client messages (e.g., ping)
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        manager.disconnect(websocket)


async def notify_state_change(message: str):
    """Send a state change notification to all clients."""
    await manager.broadcast({
        "type": "state_change",
        "timestamp": datetime.now().isoformat(),
        "message": message
    })


# Register the notification callback with idle monitor
idle_monitor.add_state_callback(notify_state_change)
