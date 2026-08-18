from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def _is_bad_ip(ip: str) -> bool:
    try:
        parsed = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return True
    return (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_reserved
        or parsed.is_multicast
        or parsed.is_unspecified
    )


def _resolve_all(host: str) -> list[str]:
    """Return every IP the hostname resolves to (v4+v6)."""
    try:
        addrs = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return []
    out: list[str] = []
    for addr in addrs:
        ip = addr[4][0]
        if ip not in out:
            out.append(ip)
    return out


def is_private_ip(host: str) -> bool:
    """True when a host resolves to any private/loopback/reserved address."""
    addrs = _resolve_all(host)
    if not addrs:
        return True
    return any(_is_bad_ip(ip) for ip in addrs)


def validate_ssrf_safe(url: str) -> None:
    """Reject URLs targeting private/internal networks (SSRF guard).

    Resolves the hostname and validates every resolved address, which defeats
    DNS-rebinding and hostname-obfuscation tricks (e.g. 169.254.169.254.nip.io).
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https URLs are allowed")
    host = (parsed.hostname or "").lower().strip().strip(".").strip("[]")
    if not host:
        raise ValueError("Empty host")
    # Literal IPv4/IPv6 -> validate directly.
    if any(c in host for c in ":") or _looks_like_ipv4(host):
        if _is_bad_ip(host):
            raise ValueError(f"Blocked IP address: {host}")
        return
    addrs = _resolve_all(host)
    if not addrs:
        raise ValueError(f"Unable to resolve host: {host}")
    for ip in addrs:
        if _is_bad_ip(ip):
            raise ValueError(f"Private/loopback host not allowed: {host} ({ip})")


def _looks_like_ipv4(host: str) -> bool:
    try:
        ipaddress.IPv4Address(host)
        return True
    except ValueError:
        return False
