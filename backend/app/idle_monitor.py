"""
Idle monitor for automatic container shutdown.
Monitors ComfyUI activity and stops the container after idle timeout.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Callable, List, Awaitable

from .config import get_config, config_manager
from .docker_manager import docker_manager, ContainerState
from .comfyui_client import comfyui_client

logger = logging.getLogger(__name__)


class ActivityEvent:
    """Represents an activity event for logging."""

    def __init__(self, event_type: str, message: str):
        self.event_type = event_type
        self.message = message
        self.timestamp = datetime.now()

    def to_dict(self):
        return {
            "type": self.event_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat()
        }


class IdleMonitor:
    """Monitors ComfyUI activity and triggers shutdown when idle."""

    def __init__(self):
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._last_check: Optional[datetime] = None
        self._activity_log: List[ActivityEvent] = []
        self._max_log_entries: int = 100
        self._state_callbacks: List[Callable[[str], Awaitable[None]]] = []

    def add_state_callback(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """Add a callback to be notified of state changes."""
        self._state_callbacks.append(callback)

    async def _notify_state_change(self, message: str) -> None:
        """Notify all registered callbacks of a state change."""
        for callback in self._state_callbacks:
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"Error in state callback: {e}")

    def _log_event(self, event_type: str, message: str) -> None:
        """Add an event to the activity log."""
        event = ActivityEvent(event_type, message)
        self._activity_log.append(event)

        # Trim old entries
        if len(self._activity_log) > self._max_log_entries:
            self._activity_log = self._activity_log[-self._max_log_entries:]

        logger.info(f"[{event_type}] {message}")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        logger.info("Idle monitor started")
        self._log_event("system", "Idle monitor started")

        while self._running:
            config = get_config()

            try:
                self._last_check = datetime.now()

                # Check if container is running
                status = docker_manager.get_status()

                if status["state"] != ContainerState.RUNNING.value:
                    # Container not running, nothing to monitor
                    await asyncio.sleep(config.poll_interval_seconds)
                    continue

                # Poll ComfyUI queue
                queue_status = await comfyui_client.get_queue_status()

                if queue_status.connected:
                    if queue_status.is_active:
                        # Activity detected, reset timer
                        self._log_event(
                            "activity",
                            f"Queue active: {queue_status.running} running, "
                            f"{queue_status.pending} pending"
                        )
                    else:
                        # Check idle time
                        idle_seconds = comfyui_client.seconds_since_activity()
                        idle_minutes = idle_seconds / 60
                        timeout_minutes = config.idle_timeout_minutes

                        logger.debug(
                            f"Idle for {idle_minutes:.1f} minutes "
                            f"(timeout: {timeout_minutes} minutes)"
                        )

                        if idle_minutes >= timeout_minutes:
                            # Idle timeout exceeded, stop container
                            self._log_event(
                                "shutdown",
                                f"Idle timeout ({timeout_minutes}m) exceeded, "
                                "stopping container"
                            )

                            result = await docker_manager.stop_container()

                            if result["success"]:
                                await self._notify_state_change("Container stopped due to idle timeout")
                            else:
                                self._log_event("error", f"Failed to stop container: {result.get('error')}")

                else:
                    # Can't connect to ComfyUI but container is running
                    # This might happen during startup, so we don't take action
                    logger.debug("Cannot connect to ComfyUI API")

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                self._log_event("error", f"Monitor error: {e}")

            await asyncio.sleep(config.poll_interval_seconds)

        logger.info("Idle monitor stopped")

    def start(self) -> None:
        """Start the idle monitor."""
        if self._running:
            logger.warning("Idle monitor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())

    def stop(self) -> None:
        """Stop the idle monitor."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    def get_activity_log(self, limit: int = 50) -> List[dict]:
        """Get recent activity log entries."""
        entries = self._activity_log[-limit:]
        return [e.to_dict() for e in reversed(entries)]

    def get_idle_info(self) -> dict:
        """Get current idle status information."""
        config = get_config()
        idle_seconds = comfyui_client.seconds_since_activity()
        idle_minutes = idle_seconds / 60
        timeout_minutes = config.idle_timeout_minutes
        remaining_minutes = max(0, timeout_minutes - idle_minutes)

        return {
            "idle_seconds": idle_seconds,
            "idle_minutes": round(idle_minutes, 1),
            "timeout_minutes": timeout_minutes,
            "remaining_minutes": round(remaining_minutes, 1),
            "will_shutdown": remaining_minutes <= 0 and docker_manager.is_running(),
            "last_check": self._last_check.isoformat() if self._last_check else None
        }

    @property
    def is_running(self) -> bool:
        """Check if the monitor is running."""
        return self._running


# Global idle monitor instance
idle_monitor = IdleMonitor()
