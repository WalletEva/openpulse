"""Adapters for various information sources."""

from .rsshub import RSSHubCollector
from .custom_rss import CustomRSSCollector

__all__ = ["RSSHubCollector", "CustomRSSCollector"]
