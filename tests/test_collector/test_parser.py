"""Tests for the parser module."""

from openpulse.collector.parser import (
    detect_language,
    html_to_text,
    truncate_text,
)


def test_html_to_text():
    """Test HTML to plain text conversion."""
    html = "<p>Hello <strong>world</strong>!</p><p>This is a <a href='#'>test</a>.</p>"
    text = html_to_text(html)
    assert "Hello" in text
    assert "world" in text
    assert "test" in text
    assert "<" not in text
    assert ">" not in text


def test_html_to_text_strips_scripts():
    """Test that script and style tags are stripped."""
    html = "<p>Content</p><script>alert('xss')</script><style>.red{color:red}</style>"
    text = html_to_text(html)
    assert "Content" in text
    assert "alert" not in text
    assert "color" not in text


def test_truncate_text():
    """Test text truncation."""
    long_text = "A" * 1000
    result = truncate_text(long_text, 100)
    assert len(result) <= 100
    assert result.endswith("...")

    short_text = "Hello"
    result = truncate_text(short_text, 100)
    assert result == "Hello"


def test_detect_language_chinese():
    """Test Chinese language detection."""
    text = "这是一个测试文本，用于检测语言识别功能。"
    assert detect_language(text) == "zh"


def test_detect_language_english():
    """Test English language detection."""
    text = "This is a test text for language detection functionality."
    assert detect_language(text) == "en"


def test_detect_language_empty():
    """Test empty text returns auto."""
    assert detect_language("") == "auto"
    assert detect_language("12345") == "auto"
