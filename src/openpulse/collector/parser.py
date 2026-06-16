"""Content parser and normalizer."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any


class HTMLTextExtractor(HTMLParser):
    """Simple HTML to plain text converter."""

    def __init__(self) -> None:
        super().__init__()
        self._result: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in ("script", "style"):
            self._skip = True
        elif tag in ("p", "br", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._result.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._result.append(data)

    def get_text(self) -> str:
        return "".join(self._result).strip()


def html_to_text(html: str) -> str:
    """Convert HTML content to plain text."""
    extractor = HTMLTextExtractor()
    extractor.feed(html)
    text = extractor.get_text()
    # Clean up excessive whitespace
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to a maximum length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text content."""
    text = re.sub(r"[\r\n]+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_urls(text: str) -> list[str]:
    """Extract all URLs from text content."""
    url_pattern = re.compile(
        r"https?://[^\s<>\"']+",
        re.IGNORECASE,
    )
    return url_pattern.findall(text)


def detect_language(text: str) -> str:
    """
    Simple language detection heuristic based on character ranges.

    Returns: 'zh' for Chinese-dominant, 'en' for English-dominant, 'auto' for mixed/other.
    """
    if not text:
        return "auto"

    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    english_chars = len(re.findall(r"[a-zA-Z]", text))

    total = chinese_chars + english_chars
    if total == 0:
        return "auto"

    if chinese_chars / total > 0.3:
        return "zh"
    elif english_chars / total > 0.7:
        return "en"
    return "auto"
