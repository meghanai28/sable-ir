import socket
from urllib.parse import urlparse

def fetch_text(url: str, transport, resolve_host) -> str:
    # Validate scheme
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    # Resolve host
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL")
    
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError("No IP address found")
    
    # Use the first resolved IP
    ip_address = ips[0]
    port = parsed.port
    
    # Determine port if not specified
    if port is None:
        if scheme == 'http':
            port = 80
        else:
            port = 443
    
    # Get the initial destination (no redirects)
    request_url = url
    
    # Make the request
    status, headers, body = transport(request_url)
    
    # Check status code
    if status != 200:
        raise ValueError("Status code is not 200")
    
    return body
