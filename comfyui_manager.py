"""
ComfyUI Process Manager
Handles starting, stopping, and monitoring the ComfyUI process.
"""

import subprocess
import threading
import time
import os
import signal
import logging
from datetime import datetime
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class ComfyUIManager:
    def __init__(
        self,
        comfyui_host: str = "127.0.0.1",
        comfyui_port: int = 8189,
        start_cmd: str = "python /root/ComfyUI/main.py --listen 127.0.0.1 --port 8189",
        idle_timeout: int = 300,
        check_interval: int = 30,
    ):
        self.comfyui_host = comfyui_host
        self.comfyui_port = comfyui_port
        self.start_cmd = start_cmd
        self.idle_timeout = idle_timeout
        self.check_interval = check_interval

        self.process: Optional[subprocess.Popen] = None
        self.last_activity: datetime = datetime.now()
        self.is_starting: bool = False
        self.lock = threading.Lock()

        self._idle_checker_thread: Optional[threading.Thread] = None
        self._stop_idle_checker = threading.Event()

    @property
    def comfyui_url(self) -> str:
        return f"http://{self.comfyui_host}:{self.comfyui_port}"

    @property
    def is_running(self) -> bool:
        """Check if ComfyUI process is running."""
        if self.process is None:
            return False
        return self.process.poll() is None

    @property
    def is_responsive(self) -> bool:
        """Check if ComfyUI is responding to requests."""
        try:
            response = requests.get(f"{self.comfyui_url}/system_stats", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def record_activity(self):
        """Record user activity to reset the idle timer."""
        self.last_activity = datetime.now()
        logger.debug("Activity recorded")

    def seconds_since_activity(self) -> float:
        """Get seconds since last activity."""
        return (datetime.now() - self.last_activity).total_seconds()

    def start_comfyui(self) -> bool:
        """Start the ComfyUI process."""
        with self.lock:
            if self.is_running:
                logger.info("ComfyUI is already running")
                return True

            if self.is_starting:
                logger.info("ComfyUI is already starting")
                return True

            self.is_starting = True

        try:
            logger.info(f"Starting ComfyUI with command: {self.start_cmd}")

            # Start the process
            self.process = subprocess.Popen(
                self.start_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid if os.name != 'nt' else None,
            )

            # Wait for ComfyUI to be responsive (max 120 seconds)
            max_wait = 120
            start_time = time.time()
            while time.time() - start_time < max_wait:
                if self.is_responsive:
                    logger.info("ComfyUI is now running and responsive")
                    self.record_activity()
                    self._start_idle_checker()
                    return True

                # Check if process died
                if self.process.poll() is not None:
                    logger.error("ComfyUI process died during startup")
                    return False

                time.sleep(1)

            logger.error("ComfyUI failed to become responsive within timeout")
            self.stop_comfyui()
            return False

        except Exception as e:
            logger.error(f"Failed to start ComfyUI: {e}")
            return False
        finally:
            self.is_starting = False

    def stop_comfyui(self):
        """Stop the ComfyUI process."""
        self._stop_idle_checker.set()

        with self.lock:
            if self.process is None:
                logger.info("ComfyUI is not running")
                return

            logger.info("Stopping ComfyUI...")

            try:
                # Send SIGTERM to process group on Unix
                if os.name != 'nt':
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                else:
                    self.process.terminate()

                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning("ComfyUI did not stop gracefully, forcing...")
                    if os.name != 'nt':
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    else:
                        self.process.kill()
                    self.process.wait()

                logger.info("ComfyUI stopped")
            except Exception as e:
                logger.error(f"Error stopping ComfyUI: {e}")
            finally:
                self.process = None

    def _start_idle_checker(self):
        """Start the background thread that checks for idle timeout."""
        self._stop_idle_checker.clear()
        self._idle_checker_thread = threading.Thread(
            target=self._idle_checker_loop,
            daemon=True
        )
        self._idle_checker_thread.start()

    def _idle_checker_loop(self):
        """Background loop that checks for idle timeout and stops ComfyUI if idle."""
        logger.info(f"Idle checker started (timeout: {self.idle_timeout}s)")

        while not self._stop_idle_checker.is_set():
            time.sleep(self.check_interval)

            if self._stop_idle_checker.is_set():
                break

            idle_seconds = self.seconds_since_activity()
            logger.debug(f"Idle for {idle_seconds:.0f}s / {self.idle_timeout}s")

            if idle_seconds >= self.idle_timeout:
                logger.info(f"Idle timeout reached ({idle_seconds:.0f}s), stopping ComfyUI")
                self.stop_comfyui()
                break

        logger.info("Idle checker stopped")

    def get_status(self) -> dict:
        """Get current status information."""
        return {
            "comfyui_running": self.is_running,
            "comfyui_responsive": self.is_responsive if self.is_running else False,
            "comfyui_starting": self.is_starting,
            "seconds_since_activity": self.seconds_since_activity(),
            "idle_timeout": self.idle_timeout,
            "time_until_shutdown": max(0, self.idle_timeout - self.seconds_since_activity()) if self.is_running else None,
        }
