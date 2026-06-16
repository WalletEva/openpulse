"""Configuration management for OpenPulse."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


def get_default_data_dir() -> Path:
    """Get the default data directory based on platform."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / ".openpulse"
    return base / "openpulse"


class OpenPulseSettings(BaseSettings):
    """Application settings loaded from environment variables and config file."""

    # Database
    database_url: str = Field(
        default="sqlite:///~/.openpulse/openpulse.db",
        description="Database connection URL (SQLite or PostgreSQL)"
    )

    # Server
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # RSSHub
    rsshub_base_url: str = Field(
        default="http://localhost:1200",
        description="RSSHub instance base URL"
    )

    # API Keys
    newsapi_key: str | None = Field(default=None, description="NewsAPI.org API key")
    youtube_api_key: str | None = Field(default=None, description="YouTube Data API key")

    # Scheduler
    scheduler_enabled: bool = Field(default=True, description="Enable/disable scheduler")
    scheduler_max_instances: int = Field(default=3, description="Max concurrent scheduler jobs")

    # Data directory
    data_dir: Path = Field(default_factory=get_default_data_dir, description="Data storage directory")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = {
        "env_prefix": "OPENPULSE_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> OpenPulseSettings:
        """Load settings from a YAML config file."""
        config_path = Path(config_path)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        return cls()

    def save_yaml(self, config_path: str | Path) -> None:
        """Save current settings to a YAML config file."""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump(exclude_none=True)
        # Convert Path objects to strings for YAML serialization
        for key, value in data.items():
            if isinstance(value, Path):
                data[key] = str(value)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def load_settings(config_path: str | Path | None = None) -> OpenPulseSettings:
    """Load settings from config file and environment variables."""
    if config_path and Path(config_path).exists():
        return OpenPulseSettings.from_yaml(config_path)
    return OpenPulseSettings()
