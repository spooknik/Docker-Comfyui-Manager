"""
ComfyUI API client for queue monitoring.
Polls the ComfyUI queue endpoint to detect activity.
"""

import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .config import get_config

logger = logging.getLogger(__name__)


class QueueStatus:
    """Represents the current queue status."""

    def __init__(
        self,
        running: int = 0,
        pending: int = 0,
        connected: bool = False,
        error: Optional[str] = None
    ):
        self.running = running
        self.pending = pending
        self.connected = connected
        self.error = error
        self.timestamp = datetime.now()

    @property
    def is_active(self) -> bool:
        """Check if there's any activity in the queue."""
        return self.running > 0 or self.pending > 0

    @property
    def total_jobs(self) -> int:
        """Get total number of jobs in queue."""
        return self.running + self.pending

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "running": self.running,
            "pending": self.pending,
            "total_jobs": self.total_jobs,
            "is_active": self.is_active,
            "connected": self.connected,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


class ComfyUIClient:
    """Client for interacting with ComfyUI's API."""

    def __init__(self):
        self._last_status: Optional[QueueStatus] = None
        self._last_activity: datetime = datetime.now()

    async def get_queue_status(self) -> QueueStatus:
        """Fetch current queue status from ComfyUI."""
        config = get_config()
        url = f"{config.comfyui_url}/queue"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()

                # ComfyUI returns: {"queue_running": [...], "queue_pending": [...]}
                running = len(data.get("queue_running", []))
                pending = len(data.get("queue_pending", []))

                status = QueueStatus(
                    running=running,
                    pending=pending,
                    connected=True
                )

                # Update last activity if there are jobs
                if status.is_active:
                    self._last_activity = datetime.now()

                self._last_status = status
                return status

        except httpx.ConnectError:
            logger.debug("Cannot connect to ComfyUI - container may be stopped")
            return QueueStatus(connected=False, error="Connection refused")

        except httpx.TimeoutException:
            logger.warning("Timeout connecting to ComfyUI")
            return QueueStatus(connected=False, error="Connection timeout")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from ComfyUI: {e}")
            return QueueStatus(connected=True, error=f"HTTP {e.response.status_code}")

        except Exception as e:
            logger.error(f"Unexpected error polling ComfyUI: {e}")
            return QueueStatus(connected=False, error=str(e))

    async def is_healthy(self) -> bool:
        """Check if ComfyUI is responding."""
        config = get_config()
        url = f"{config.comfyui_url}/system_stats"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception:
            return False

    async def wait_for_ready(self, timeout_seconds: int = 120) -> bool:
        """Wait for ComfyUI to become ready after starting."""
        import asyncio

        start_time = datetime.now()
        check_interval = 2  # seconds

        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            if await self.is_healthy():
                logger.info("ComfyUI is ready")
                return True
            await asyncio.sleep(check_interval)

        logger.warning(f"ComfyUI did not become ready within {timeout_seconds}s")
        return False

    def update_activity(self) -> None:
        """Manually update last activity timestamp (e.g., on proxy request)."""
        self._last_activity = datetime.now()

    @property
    def last_activity(self) -> datetime:
        """Get timestamp of last detected activity."""
        return self._last_activity

    @property
    def last_status(self) -> Optional[QueueStatus]:
        """Get the last fetched queue status."""
        return self._last_status

    def seconds_since_activity(self) -> float:
        """Get seconds since last activity."""
        return (datetime.now() - self._last_activity).total_seconds()


# Global ComfyUI client instance
comfyui_client = ComfyUIClient()
