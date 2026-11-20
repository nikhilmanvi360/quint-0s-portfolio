"""
QuintOS APISentry — Zero-Trust SSRF Defense Engine
Author: Nikhil Manvi

Defensive perimeter firewall preventing Server-Side Request Forgery (SSRF)
attacks during live API probing and TLS header inspection.
"""

import ipaddress
import socket
from typing import Tuple
from urllib.parse import urlparse

# Explicitly blocked RFC 1918 private subnets, loopback, and link-local ranges
DISALLOWED_IPV4_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / Cloud metadata
    ipaddress.ip_network("100.64.0.0/10"),   # Carrier-grade NAT
]

DISALLOWED_IPV6_NETWORKS = [
    ipaddress.ip_network("::1/128"),         # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),        # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),       # Link-local
]

BLOCKED_CANONICAL_HOSTNAMES = {
    "localhost",
    "broadcasthost",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
    "169.254.169.254",                      # AWS / GCP / Azure metadata endpoint
}


def is_ssrf_vulnerable_target(url: str, allow_loopback_for_testing: bool = False) -> Tuple[bool, str]:
    """
    Evaluates whether an outbound probe target resolves to a private or restricted network.
    
    Protects against:
    - Internal port scanning across RFC 1918 networks.
    - Cloud instance metadata token theft (169.254.169.254).
    - DNS Rebinding / Split-horizon IP resolution attacks.

    Returns:
        (is_blocked: bool, rejection_reason: str)
    """
    if not url:
        return True, "Empty target URL provided"

    try:
        parsed = urlparse(url)
    except Exception as exc:
        return True, f"Malformed URL structure: {exc}"

    if parsed.scheme.lower() not in ("http", "https"):
        return True, f"Unsupported protocol scheme '{parsed.scheme}'. Only HTTP/HTTPS permitted."

    hostname = parsed.hostname
    if not hostname:
        return True, "Target URL missing valid hostname component"

    hostname_lower = hostname.strip("[]").lower()

    if hostname_lower in BLOCKED_CANONICAL_HOSTNAMES:
        if allow_loopback_for_testing and hostname_lower in ("localhost", "127.0.0.1", "::1"):
            return False, "Allowed under explicit test flag"
        return True, f"Target hostname '{hostname_lower}' is on the restricted infrastructure blacklist"

    # Resolve all associated A and AAAA DNS records to mitigate DNS Rebinding
    try:
        resolved_ips = socket.getaddrinfo(hostname_lower, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        return True, f"DNS resolution failed for hostname '{hostname_lower}': {exc}"

    for entry in resolved_ips:
        sockaddr = entry[4]
        ip_str = sockaddr[0]

        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return True, f"Invalid IP representation encountered: {ip_str}"

        # Loopback bypass check for controlled lab environments
        if allow_loopback_for_testing and ip_obj.is_loopback:
            continue

        if ip_obj.version == 4:
            for forbidden_net in DISALLOWED_IPV4_NETWORKS:
                if ip_obj in forbidden_net:
                    return True, f"Target resolves to restricted internal IPv4 subnet: {forbidden_net}"
        elif ip_obj.version == 6:
            for forbidden_net in DISALLOWED_IPV6_NETWORKS:
                if ip_obj in forbidden_net:
                    return True, f"Target resolves to restricted internal IPv6 subnet: {forbidden_net}"

    return False, "Target cleared for outbound security evaluation"
