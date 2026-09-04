import ipaddress
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    port = parsed.port
    if port is None:
        if scheme == 'http':
            port = 80
        else:
            port = 443
    
    if scheme == 'http' and port != 80:
        raise ValueError("Invalid port for HTTP")
    if scheme == 'https' and port != 443:
        raise ValueError("Invalid port for HTTPS")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    resolved_ips = resolve_host(hostname)
    for ip_str in resolved_ips:
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError("Invalid IP address")
        
        if addr.is_loopback:
            raise ValueError("Loopback address not allowed")
        if addr.is_private:
            raise ValueError("Private address not allowed")
        if addr.is_link_local:
            raise ValueError("Link-local address not allowed")
        if addr.is_multicast:
            raise ValueError("Multicast address not allowed")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Unexpected status code")
    
    return body
