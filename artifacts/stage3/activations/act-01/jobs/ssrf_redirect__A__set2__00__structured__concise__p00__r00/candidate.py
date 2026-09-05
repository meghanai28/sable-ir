import socket
from urllib.parse import urlparse

def fetch_text(url: str, transport, resolve_host) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    port = parsed.port
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
    
    netloc = parsed.netloc
    if not netloc:
        raise ValueError("Invalid URL: missing netloc.")
    
    hostname = netloc.split(':')[0]
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve hostname.")
    
    if not ip_addresses:
        raise ValueError("Failed to resolve hostname.")
    
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError("Only status code 200 is allowed.")
    
    return body
