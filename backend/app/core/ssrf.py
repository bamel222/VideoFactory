from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_PREFIXES = [
    "10.", "127.", "169.254.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
    "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
    "192.168.", "0.", "100.100.100.", "0x", "::", "fe80:", "fc", "fd",
]


def is_private_ip(host: str) -> bool:
    try:
        addrs = socket.getaddrinfo(host, None)
    except Exception:
        return True
    for addr in addrs:
        ip = addr[4][0]
        try:
            parsed = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if parsed.is_private or parsed.is_loopback or parsed.is_link_local or parsed.is_reserved:
            return True
    return False


def validate_ssrf_safe(url: str) -> None:
    """Reject URLs pointing at private/internal networks (SSRF guard)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https URLs are allowed")
    host = parsed.hostname or ""
    if any(host.startswith(p) for p in BLOCKED_PREFIXES):
        raise ValueError(f"Blocked host prefix: {host}")
    if is_private_ip(host):
        raise ValueError(f"Private/loopback host not allowed: {host}")
