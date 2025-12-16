"""
Docker container management for ComfyUI.
Handles starting, stopping, and monitoring the ComfyUI container.
"""

import docker
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from .config import get_config

logger = logging.getLogger(__name__)


class ContainerState(str, Enum):
    """Possible states of the container."""
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    NOT_FOUND = "not_found"


class DockerManager:
    """Manages Docker container operations for ComfyUI."""

    def __init__(self):
        self._client: Optional[docker.DockerClient] = None
        self._state: ContainerState = ContainerState.STOPPED
        self._state_changed_at: datetime = datetime.now()

    @property
    def client(self) -> docker.DockerClient:
        """Get or create Docker client."""
        if self._client is None:
            config = get_config()
            self._client = docker.DockerClient(base_url=f"unix://{config.docker_socket}")
        return self._client

    def _get_container(self) -> Optional[docker.models.containers.Container]:
        """Get the ComfyUI container by name."""
        config = get_config()
        try:
            return self.client.containers.get(config.container_name)
        except docker.errors.NotFound:
            logger.warning(f"Container '{config.container_name}' not found")
            return None
        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get current container status."""
        container = self._get_container()

        if container is None:
            self._state = ContainerState.NOT_FOUND
            return {
                "state": self._state.value,
                "container_exists": False,
                "message": "Container not found"
            }

        status = container.status

        # Map Docker status to our states
        if status == "running":
            self._state = ContainerState.RUNNING
        elif status in ("created", "restarting"):
            self._state = ContainerState.STARTING
        elif status in ("paused", "exited", "dead"):
            self._state = ContainerState.STOPPED
        else:
            self._state = ContainerState.ERROR

        # Get container details
        container.reload()
        attrs = container.attrs

        started_at = None
        if attrs.get("State", {}).get("StartedAt"):
            started_at = attrs["State"]["StartedAt"]

        return {
            "state": self._state.value,
            "container_exists": True,
            "docker_status": status,
            "container_id": container.short_id,
            "container_name": container.name,
            "started_at": started_at,
            "image": container.image.tags[0] if container.image.tags else None,
        }

    async def start_container(self) -> Dict[str, Any]:
        """Start the ComfyUI container."""
        container = self._get_container()

        if container is None:
            return {
                "success": False,
                "error": "Container not found",
                "state": ContainerState.NOT_FOUND.value
            }

        current_status = container.status
        if current_status == "running":
            return {
                "success": True,
                "message": "Container already running",
                "state": ContainerState.RUNNING.value
            }

        self._state = ContainerState.STARTING
        self._state_changed_at = datetime.now()

        try:
            logger.info(f"Starting container: {container.name}")
            container.start()

            # Wait briefly for container to start
            container.reload()

            if container.status == "running":
                self._state = ContainerState.RUNNING
                self._state_changed_at = datetime.now()
                return {
                    "success": True,
                    "message": "Container started successfully",
                    "state": ContainerState.RUNNING.value
                }
            else:
                return {
                    "success": True,
                    "message": "Container start initiated",
                    "state": ContainerState.STARTING.value
                }

        except docker.errors.APIError as e:
            logger.error(f"Failed to start container: {e}")
            self._state = ContainerState.ERROR
            return {
                "success": False,
                "error": str(e),
                "state": ContainerState.ERROR.value
            }

    async def stop_container(self) -> Dict[str, Any]:
        """Stop the ComfyUI container."""
        container = self._get_container()

        if container is None:
            return {
                "success": False,
                "error": "Container not found",
                "state": ContainerState.NOT_FOUND.value
            }

        current_status = container.status
        if current_status != "running":
            return {
                "success": True,
                "message": "Container already stopped",
                "state": ContainerState.STOPPED.value
            }

        self._state = ContainerState.STOPPING
        self._state_changed_at = datetime.now()

        try:
            logger.info(f"Stopping container: {container.name}")
            container.stop(timeout=30)

            self._state = ContainerState.STOPPED
            self._state_changed_at = datetime.now()

            return {
                "success": True,
                "message": "Container stopped successfully",
                "state": ContainerState.STOPPED.value
            }

        except docker.errors.APIError as e:
            logger.error(f"Failed to stop container: {e}")
            self._state = ContainerState.ERROR
            return {
                "success": False,
                "error": str(e),
                "state": ContainerState.ERROR.value
            }

    def get_logs(self, tail: int = 100) -> List[str]:
        """Get recent container logs."""
        container = self._get_container()

        if container is None:
            return ["Container not found"]

        try:
            logs = container.logs(tail=tail, timestamps=True).decode("utf-8")
            return logs.strip().split("\n") if logs.strip() else []
        except docker.errors.APIError as e:
            logger.error(f"Failed to get logs: {e}")
            return [f"Error getting logs: {e}"]

    def is_running(self) -> bool:
        """Check if the container is currently running."""
        container = self._get_container()
        return container is not None and container.status == "running"

    @property
    def state(self) -> ContainerState:
        """Get current cached state."""
        return self._state

    @property
    def state_changed_at(self) -> datetime:
        """Get timestamp of last state change."""
        return self._state_changed_at


# Global Docker manager instance
docker_manager = DockerManager()
