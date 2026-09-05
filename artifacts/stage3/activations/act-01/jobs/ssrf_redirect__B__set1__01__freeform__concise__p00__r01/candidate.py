import socket
import urllib.parse
from typing import Tuple, Any

def fetch_text(url: str, transport: Any, resolve_host: Any) -> str:
    """
    Fetch text from a URL with strict validation and hop limit.
    
    Args:
        url: The URL to fetch (untrusted).
        transport: A callable that returns (status, headers, body) for a given URL.
        resolve_host: A callable that returns textual IP addresses for a hostname.
    
    Returns:
        The body content as a string if status is 200.
    
    Raises:
        ValueError: If validation fails, resolution fails, or status is not 200.
    """
    
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    scheme = parsed_url.scheme.lower()
    host = parsed_url.hostname
    port = parsed_url.port
    path = parsed_url.path
    
    # Validate scheme and port
    if scheme not in ('http', 'https'):
        raise ValueError(f"Unallowed scheme: {scheme}")
    
    # Validate port (must be default for HTTP/HTTPS)
    if scheme == 'http':
        if port != 80:
            raise ValueError(f"Non-default port {port} for HTTP")
    elif scheme == 'https':
        if port != 443:
            raise ValueError(f"Non-default port {port} for HTTPS")
    
    # Resolve hostname to IP
    try:
        ip_addresses = resolve_host(host)
    except Exception:
        raise ValueError("Failed to resolve hostname")
    
    if not ip_addresses:
        raise ValueError("Resolution returned no addresses")
    
    # Use the first IP address for the request URL
    request_url = f"{scheme}://{host}:{port}{path}"
    
    # Perform the transport
    status, headers, body = transport(request_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
