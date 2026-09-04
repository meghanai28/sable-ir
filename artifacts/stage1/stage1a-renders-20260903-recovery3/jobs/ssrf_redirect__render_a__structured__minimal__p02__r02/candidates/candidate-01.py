import ipaddress
import re
from urllib.parse import urlparse

def _is_public_ip(ip_str):
    try:
        addr = ipaddress.ip_address(ip_str)
        if addr.is_private:
            return False
        if addr.is_loopback:
            return False
        if addr.is_reserved:
            return False
        if addr.is_multicast:
            return False
        if addr.is_link_local:
            return False
        if addr.version == 4:
            if addr.is_global:
                return True
            if int(addr) == 0:
                return False
            if addr == ipaddress.IPv4Address("255.255.255.255"):
                return False
            return True
        if addr.version == 6:
            if addr.is_global:
                return True
            if addr == ipaddress.IPv6Address("::"):
                return False
            if addr == ipaddress.IPv6Address("::1"):
                return False
            return True
        return False
    except ValueError:
        return False

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    
    scheme = parsed.scheme
    if scheme not in ("http", "https"):
        raise ValueError("Invalid scheme")
    
    host = parsed.hostname
    if host is None:
        raise ValueError("Missing hostname")
    
    port = parsed.port
    if scheme == "http" and port is not None and port != 80:
        raise ValueError("Invalid port for http")
    if scheme == "https" and port is not None and port != 443:
        raise ValueError("Invalid port for https")
    
    ips = resolve_host(host)
    if not ips:
        raise ValueError("No IPs resolved")
    
    for ip in ips:
        if not _is_public_ip(ip):
            raise ValueError("Non-public IP")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body
