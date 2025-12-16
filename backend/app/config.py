"""
Configuration management for ComfyUI Docker Manager.
Handles environment variables and persistent config storage.
"""

import os
import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional


class Config(BaseModel):
    """Application configuration."""

    # Docker settings
    container_name: str = "comfyui"
    docker_socket: str = "/var/run/docker.sock"

    # ComfyUI settings
    comfyui_host: str = "comfyui"  # Docker network hostname
    comfyui_port: int = 8188

    # Idle detection settings
    idle_timeout_minutes: int = 30
    poll_interval_seconds: int = 30

    # Auto-start settings
    auto_start_enabled: bool = True
    startup_timeout_seconds: int = 120

    # Manager settings
    manager_port: int = 8080
    proxy_port: int = 8188

    @property
    def comfyui_url(self) -> str:
        return f"http://{self.comfyui_host}:{self.comfyui_port}"


class ConfigManager:
    """Manages configuration loading, saving, and updates."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or os.getenv(
            "CONFIG_PATH",
            "/app/data/config.json"
        ))
        self._config: Optional[Config] = None

    def load(self) -> Config:
        """Load configuration from environment and file."""
        # Start with defaults
        config_dict = {}

        # Load from file if exists
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    config_dict = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        # Override with environment variables
        env_mappings = {
            "COMFYUI_CONTAINER_NAME": "container_name",
            "DOCKER_SOCKET": "docker_socket",
            "COMFYUI_HOST": "comfyui_host",
            "COMFYUI_PORT": ("comfyui_port", int),
            "IDLE_TIMEOUT_MINUTES": ("idle_timeout_minutes", int),
            "POLL_INTERVAL_SECONDS": ("poll_interval_seconds", int),
            "AUTO_START_ENABLED": ("auto_start_enabled", lambda x: x.lower() == "true"),
            "STARTUP_TIMEOUT_SECONDS": ("startup_timeout_seconds", int),
            "MANAGER_PORT": ("manager_port", int),
            "PROXY_PORT": ("proxy_port", int),
        }

        for env_var, mapping in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                if isinstance(mapping, tuple):
                    key, converter = mapping
                    config_dict[key] = converter(value)
                else:
                    config_dict[mapping] = value

        self._config = Config(**config_dict)
        return self._config

    def save(self) -> None:
        """Save current configuration to file."""
        if self._config is None:
            return

        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump(self._config.model_dump(), f, indent=2)

    def update(self, **kwargs) -> Config:
        """Update configuration with new values."""
        if self._config is None:
            self.load()

        current_dict = self._config.model_dump()
        current_dict.update(kwargs)
        self._config = Config(**current_dict)
        self.save()
        return self._config

    @property
    def config(self) -> Config:
        """Get current configuration, loading if necessary."""
        if self._config is None:
            self.load()
        return self._config


# Global config manager instance
config_manager = ConfigManager()


def get_config() -> Config:
    """Get the current configuration."""
    return config_manager.config
