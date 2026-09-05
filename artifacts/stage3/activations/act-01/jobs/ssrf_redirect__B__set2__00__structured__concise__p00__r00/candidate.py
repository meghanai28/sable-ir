import socket
import urllib.parse
from typing import Tuple, List, Optional

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL to extract scheme, netloc, and path
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc
    port = parsed.port

    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")

    # Validate port
    if scheme == 'http':
        default_port = 80
    elif scheme == 'https':
        default_port = 443
    else:
        raise ValueError(f"Unknown scheme: {scheme}")

    if port is not None and port != default_port:
        raise ValueError(f"Port {port} is not the default port for {scheme}")

    # Resolve hostname
    hostname = netloc
    # Remove credentials if present (e.g., user:pass@host)
    if '@' in hostname:
        hostname = hostname.split('@')[-1]
    
    # Resolve to IP addresses
    ip_addresses = resolve_host(hostname)
    
    # Validate resolved hostnames
    for ip in ip_addresses:
        # Check if the IP starts with http or https on its default port (conceptually, the IP itself doesn't, but the original check implies the resolved entity must be safe)
        # The plan says: "start with http or https on its default port" - this likely refers to the original URL validation logic applied to the resolved target if it were a URL, or simply ensuring no public IP is used.
        # However, the plan says: "raise ValueError unless its textual IP addresses do all of the following: start with http or https on its default port".
        # An IP address does not start with http. This implies the check is on the *original* URL's scheme/port which we already did, but the plan phrasing suggests we must ensure the resolved host doesn't point to a public address if it were a URL, OR it's a constraint on the input format.
        # Re-reading: "raise ValueError unless its textual IP addresses do all of the following: start with http or https on its default port". This is logically impossible for an IP string.
        # Likely interpretation from the context of "TRUST: ... may point to another host": The resolved host should not be a public address.
        # But the explicit condition "start with http..." suggests we might be checking if the resolved entity *could* be interpreted as a URL or if the validation failed.
        # Actually, looking at the plan's "GUARD": "raise ValueError unless its textual IP addresses do all of the following...".
        # This is a constraint on the *result* of resolve_host. If resolve_host returns IPs, they don't start with http.
        # Perhaps the plan implies: if the resolved host is a public IP, raise ValueError.
        # Let's assume the standard security guard: do not resolve to public IPs.
        # But to strictly follow "start with http or https", maybe it means if the resolved host is not an IP (e.g. domain), it fails? No, resolve_host returns IPs.
        # Let's interpret "start with http" as a check on the *original* URL which we already did, and the IP check is about public vs private.
        # However, if I must follow the plan literally: "raise ValueError unless its textual IP addresses do all of the following: start with http or https on its default port".
        # This condition is never met for an IP. Thus, any IP would trigger ValueError? That breaks functionality.
        # Alternative interpretation: The plan describes the *requirements* for the URL. If the resolved host is a public address, it fails the "not be a public address" check.
        # Let's assume the "start with http" part is a copy-paste artifact in the plan description or refers to the scheme check we already did. The critical part is "not be a public address".
        # I will implement the check: if the resolved IP is a public address, raise ValueError.
        if is_public_ip(ip):
            raise ValueError(f"Resolved host {hostname} is a public address")

    # Fetch the resource
    status, headers, body = transport(url)

    # Return body only for status 200
    if status == 200:
        return body
    else:
        raise ValueError(f"Unexpected status code: {status}")

def is_public_ip(ip: str) -> bool:
    # Basic check for public IPs (not 127.0.0.1, not 10.x.x.x, etc.)
    # This is a simplified check as per the "safety document is not available" constraint.
    # We assume any IP not in private ranges is public.
    private_prefixes = ['127.', '10.', '192.168.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.', '169.254.']
    for prefix in private_prefixes:
        if ip.startswith(prefix):
            return False
    # Also check for loopback IPv6
    if ip.startswith('::1'):
        return False
    # Assume anything else is public for the purpose of this exercise
    return True
