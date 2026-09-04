import re
import ipaddress
from urllib.parse import urlparse, urljoin


def _validate_scheme(parsed):
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError("Invalid scheme")
    return scheme


def _validate_port(scheme, parsed):
    if parsed.port is None:
        return
    if scheme == "http" and parsed.port != 80:
        raise ValueError("Invalid port for HTTP")
    if scheme == "https" and parsed.port != 443:
        raise ValueError("Invalid port for HTTPS")


def _validate_credentials(parsed):
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials not allowed")


def _is_public_address(addr):
    try:
        ip = ipaddress.ip_address(addr)
        return ip.is_global and not ip.is_loopback and not ip.is_multicast and not ip.is_reserved and not ip.is_unspecified
    except ValueError:
        return False


def _validate_host(hostname, resolve_host):
    if not hostname:
        raise ValueError("Empty hostname")
    try:
        ip = ipaddress.ip_address(hostname)
        if not _is_public_address(str(ip)):
            raise ValueError("Non-public IP address")
        return
    except ValueError:
        pass
    addresses = resolve_host(hostname)
    if not addresses:
        raise ValueError("No DNS resolution")
    for addr in addresses:
        if not _is_public_address(addr):
            raise ValueError("Non-public IP address in DNS resolution")


def _validate_url(url, resolve_host):
    parsed = urlparse(url)
    scheme = _validate_scheme(parsed)
    _validate_port(scheme, parsed)
    _validate_credentials(parsed)
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("No hostname")
    _validate_host(hostname, resolve_host)
    return parsed


def fetch_text(url, transport, resolve_host):
    current_url = url
    hops = 0
    
    while True:
        parsed = _validate_url(current_url, resolve_host)
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 307, 308):
            hops += 1
            if hops > 5:
                raise ValueError("Too many redirects")
            
            location = None
            for key, value in headers.items() if isinstance(headers, dict) else headers:
                if key.lower() == "location":
                    location = value
                    break
            
            if location is None:
                raise ValueError("Missing Location header")
            
            current_url = urljoin(current_url, location)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
