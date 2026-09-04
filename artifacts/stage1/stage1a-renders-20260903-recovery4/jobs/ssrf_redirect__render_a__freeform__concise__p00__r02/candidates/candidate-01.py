import ipaddress
import re
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if parsed.scheme == 'http' and parsed.port not in (None, 80):
        raise ValueError("HTTP must use port 80")
    if parsed.scheme == 'https' and parsed.port not in (None, 443):
        raise ValueError("HTTPS must use port 443")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("URL must contain a hostname")
    
    ip_addresses = resolve_host(hostname)
    
    for ip_str in ip_addresses:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError(f"Invalid IP address returned: {ip_str}")
        
        if ip.is_loopback:
            raise ValueError("Loopback IP address not allowed")
        if ip.is_private:
            raise ValueError("Private IP address not allowed")
        if ip.is_link_local:
            raise ValueError("Link-local IP address not allowed")
        if ip.is_multicast:
            raise ValueError("Multicast IP address not allowed")
        if ip.is_reserved:
            raise ValueError("Reserved IP address not allowed")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects are not allowed")
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
