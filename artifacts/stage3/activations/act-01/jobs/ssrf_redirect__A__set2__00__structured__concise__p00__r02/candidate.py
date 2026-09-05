import socket
import urllib.parse

def fetch_text(url: str, transport, resolve_host) -> str:
    parsed_url = urllib.parse.urlparse(url)
    scheme = parsed_url.scheme.lower()
    
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if scheme == 'http':
        port = 80
    else:
        port = 443
    
    if parsed_url.port:
        target_port = parsed_url.port
    else:
        target_port = port
    
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    # Check for path traversal in the URL path
    path = parsed_url.path
    if '..' in path:
        raise ValueError("Path traversal detected")
    
    # Resolve hostname to IP
    try:
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError("Failed to resolve hostname")
    except Exception:
        raise ValueError("Failed to resolve hostname")
    
    # Make the request
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body.decode('utf-8') if isinstance(body, bytes) else body
