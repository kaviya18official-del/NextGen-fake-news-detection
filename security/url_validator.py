"""SSRF and Safe URL validation module for NextGen NewsVerify.

Prevents Server-Side Request Forgery (SSRF) and DNS rebinding attacks by
validating URL schemes, ports, hostnames, and resolved IP addresses against
private, loopback, link-local, multicast, and cloud metadata ranges.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Tuple, List, Optional
from urllib.parse import urlparse
import requests

# Allowed URL schemes
ALLOWED_SCHEMES = {"http", "https"}

# Allowed destination ports
ALLOWED_PORTS = {80, 443, 8080}

# Forbidden hostnames (case-insensitive)
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata",
    "instance-data",
    "169.254.169.254",
    "0.0.0.0",
}

# Blocked IP networks (IPv4 and IPv6)
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("10.0.0.0/8"),         # Private RFC1918
    ipaddress.ip_network("100.64.0.0/10"),      # Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / Cloud metadata
    ipaddress.ip_network("172.16.0.0/12"),      # Private RFC1918
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),     # Private RFC1918
    ipaddress.ip_network("198.18.0.0/15"),      # Network benchmark tests
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6 blocked
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-local
    ipaddress.ip_network("ff00::/8"),           # Multicast
]


def is_ip_blocked(ip_addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if an IP address belongs to any blocked or private network."""
    if ip_addr.is_loopback or ip_addr.is_private or ip_addr.is_link_local or ip_addr.is_multicast or ip_addr.is_reserved or ip_addr.is_unspecified:
        return True
    for net in BLOCKED_NETWORKS:
        if ip_addr in net:
            return True
    return False


def is_safe_url(url: str) -> Tuple[bool, str]:
    """Validate a URL against SSRF, dangerous schemes, ports, and internal destinations.

    Returns:
        (True, "") if safe.
        (False, reason_str) if unsafe.
    """
    if not url or not isinstance(url, str):
        return False, "Empty or invalid URL"

    url = url.strip()
    if len(url) > 2048:
        return False, "URL exceeds maximum length of 2048 characters"

    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Failed to parse URL: {e}"

    # Check scheme
    if not parsed.scheme or parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False, f"Unsupported scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted."

    # Check hostname
    hostname = parsed.hostname
    if not hostname:
        return False, "URL must contain a valid hostname"

    hostname_lower = hostname.lower()
    if hostname_lower in BLOCKED_HOSTNAMES or hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
        return False, f"Access to internal or reserved hostname '{hostname}' is forbidden."

    # Check port
    port = parsed.port
    if port is not None and port not in ALLOWED_PORTS:
        return False, f"Port {port} is not allowed. Only ports {ALLOWED_PORTS} are supported."

    # Check if host is direct IP address
    try:
        ip = ipaddress.ip_address(hostname)
        if is_ip_blocked(ip):
            return False, f"Destination IP {ip} is restricted (private/loopback/cloud metadata)."
        return True, ""
    except ValueError:
        pass  # Hostname is a domain name, proceed to DNS resolution

    # Resolve DNS to check all candidate IPs
    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        return False, f"DNS resolution failed for hostname '{hostname}': {e}"
    except Exception as e:
        return False, f"Error resolving hostname '{hostname}': {e}"

    if not addr_info:
        return False, f"No IP addresses resolved for hostname '{hostname}'"

    resolved_ips: List[str] = []
    for entry in addr_info:
        ip_str = entry[4][0]
        resolved_ips.append(ip_str)
        try:
            ip = ipaddress.ip_address(ip_str)
            if is_ip_blocked(ip):
                return False, f"Hostname '{hostname}' resolves to restricted IP {ip_str}."
        except ValueError:
            return False, f"Invalid resolved IP address '{ip_str}'"

    return True, ""


class SafeUrlFetcher:
    """Safe HTTP client with SSRF guards, redirect re-validation, timeouts, and byte limits."""

    DEFAULT_USER_AGENT = "NextGenNewsVerify/1.0 (+https://newsverify.local; Investigative Research)"
    MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB
    CONNECT_TIMEOUT = 4.0
    READ_TIMEOUT = 8.0
    MAX_REDIRECTS = 3

    def __init__(self, user_agent: Optional[str] = None):
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT

    def fetch(self, url: str) -> requests.Response:
        """Safely fetch a URL following redirects with SSRF re-validation at each hop."""
        current_url = url
        redirect_count = 0

        session = requests.Session()
        session.headers.update({"User-Agent": self.user_agent})

        while redirect_count <= self.MAX_REDIRECTS:
            # Validate URL before every request (including redirects)
            is_safe, reason = is_safe_url(current_url)
            if not is_safe:
                raise ValueError(f"Blocked URL access ({reason})")

            resp = session.get(
                current_url,
                allow_redirects=False,
                stream=True,
                timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT),
            )

            # Check for redirect status codes
            if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location")
                if not location:
                    raise ValueError("Redirect received without Location header")

                # Resolve relative redirects
                from urllib.parse import urljoin
                current_url = urljoin(current_url, location)
                redirect_count += 1
                resp.close()
                continue

            # Read content with byte limit enforcement
            content_chunks = []
            total_bytes = 0
            for chunk in resp.iter_content(chunk_size=16384):
                if chunk:
                    total_bytes += len(chunk)
                    if total_bytes > self.MAX_RESPONSE_BYTES:
                        resp.close()
                        raise ValueError(f"Response exceeds maximum allowed size ({self.MAX_RESPONSE_BYTES} bytes)")
                    content_chunks.append(chunk)

            # Set raw content and return response
            resp._content = b"".join(content_chunks)
            return resp

        raise ValueError(f"Maximum redirect limit ({self.MAX_REDIRECTS}) exceeded")
