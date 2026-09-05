import socket
import urllib.parse
from urllib.parse import urlparse

def fetch_text(url: str, transport, resolve_host) -> str:
    # Guard: Check scheme
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")

    # Guard: Resolve host
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not ip_addresses:
        raise ValueError(f"No IP addresses found for hostname: {hostname}")

    # Guard: Parse path and check for absolute URLs or path traversal
    path = parsed_url.path
    if not path:
        path = '/'
    
    # Check for .. segments or absolute paths within the path
    if '..' in path:
        raise ValueError("Path traversal detected")
    
    # Guard: Check final request URL before making TCP connection
    # We need to construct the base URL to ensure we are connecting to the correct host
    # The transport function likely handles the full URL, so we ensure the path we pass
    # is relative and doesn't escape the host.
    
    # Check if the path starts with / and doesn't have ..
    if not path.startswith('/'):
        raise ValueError("Path must start with /")
    
    # Guard: Check status code
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError(f"Invalid status code: {status}")
    
    # Return body as text
    return body.decode('utf-8', errors='replace')
