"""Tests for SSRF prevention and URL validation in security/url_validator.py."""

import pytest
from unittest.mock import patch, MagicMock
from security.url_validator import is_safe_url, SafeUrlFetcher, is_ip_blocked
import ipaddress


def test_allowed_public_urls():
    """Verify standard legitimate public news domains are allowed."""
    safe_urls = [
        "https://www.reuters.com/world/us/example-story",
        "https://apnews.com/article/example-12345",
        "http://bbc.com/news/world-67890",
    ]
    for url in safe_urls:
        safe, reason = is_safe_url(url)
        assert safe is True, f"Expected {url} to be safe, got: {reason}"
        assert reason == ""


def test_reject_unsupported_schemes():
    """Verify dangerous or non-HTTP schemes are blocked."""
    unsafe_schemes = [
        "ftp://example.com/file.txt",
        "file:///etc/passwd",
        "gopher://example.com",
        "dict://example.com",
        "javascript:alert(1)",
        "data:text/html,hello",
    ]
    for url in unsafe_schemes:
        safe, reason = is_safe_url(url)
        assert safe is False
        assert "scheme" in reason.lower() or "unsupported" in reason.lower() or "parse" in reason.lower()


def test_reject_internal_and_private_hostnames():
    """Verify localhost and cloud metadata hostnames are blocked immediately."""
    blocked_hosts = [
        "http://localhost/admin",
        "http://127.0.0.1:8080/metrics",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://0.0.0.0/",
    ]
    for url in blocked_hosts:
        safe, reason = is_safe_url(url)
        assert safe is False
        assert any(term in reason.lower() for term in ["restricted", "forbidden", "internal", "blocked"])


def test_reject_disallowed_ports():
    """Verify non-standard web ports are rejected."""
    bad_ports = [
        "http://example.com:22/ssh",
        "http://example.com:25/smtp",
        "http://example.com:3306/db",
        "https://example.com:8443/custom",
    ]
    for url in bad_ports:
        safe, reason = is_safe_url(url)
        assert safe is False
        assert "port" in reason.lower()


def test_ip_range_blocking():
    """Verify comprehensive IP address range blocking."""
    assert is_ip_blocked(ipaddress.ip_address("127.0.0.1")) is True
    assert is_ip_blocked(ipaddress.ip_address("10.50.1.1")) is True
    assert is_ip_blocked(ipaddress.ip_address("172.16.0.5")) is True
    assert is_ip_blocked(ipaddress.ip_address("192.168.1.100")) is True
    assert is_ip_blocked(ipaddress.ip_address("169.254.169.254")) is True
    assert is_ip_blocked(ipaddress.ip_address("::1")) is True
    assert is_ip_blocked(ipaddress.ip_address("8.8.8.8")) is False
    assert is_ip_blocked(ipaddress.ip_address("1.1.1.1")) is False


def test_safe_fetcher_redirect_validation():
    """Verify SafeUrlFetcher re-validates URLs upon redirect to prevent SSRF hopping."""
    fetcher = SafeUrlFetcher()
    with patch("requests.Session.get") as mock_get:
        # Simulate redirect to internal metadata service
        mock_resp_1 = MagicMock()
        mock_resp_1.is_redirect = True
        mock_resp_1.status_code = 302
        mock_resp_1.headers = {"Location": "http://169.254.169.254/secret"}

        mock_get.return_value = mock_resp_1

        with pytest.raises(ValueError, match="Blocked URL access"):
            fetcher.fetch("https://reuters.com/story")
