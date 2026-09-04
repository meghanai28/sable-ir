import ipaddress
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    scheme = parsed.scheme
    hostname = parsed.hostname
    port = parsed.port
    
    if not scheme or not hostname:
        raise ValueError("Invalid URL")
    
    if scheme == "http":
        if port is not None and port != 80:
            raise ValueError("Invalid port for http")
    elif scheme == "https":
        if port is not None and port != 443:
            raise ValueError("Invalid port for https")
    else:
        raise ValueError("Invalid scheme")
    
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError("No IP addresses resolved")
    
    for addr in ip_addresses:
        ip = ipaddress.ip_address(addr)
        if ip.is_loopback:
            raise ValueError("Loopback address not allowed")
        if ip.is_private:
            raise ValueError("Private address not allowed")
        if ip.is_link_local:
            raise ValueError("Link-local address not allowed")
        if ip.is_multicast:
            raise ValueError("Multicast address not allowed")
        if ip.is_reserved:
            raise ValueError("Reserved address not allowed")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects not allowed")
    
    if status == 200:
        return body
    
    raise ValueError(f"Unexpected status code: {status}")
