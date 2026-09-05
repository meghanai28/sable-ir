import socket
import urllib.parse
from typing import Tuple, List, Optional

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL using the provided transport and host resolver.
    
    Args:
        url: The URL to fetch (untrusted input).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: For disallowed requests or failed host resolution.
    """
    # Parse the URL to extract the host and port
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Extract host and port
    host = parsed.hostname
    if not host:
        raise ValueError("URL must contain a valid hostname")
    
    port = parsed.port
    if port is None:
        # Use default ports
        if parsed.scheme == 'http':
            port = 80
        else:
            port = 443
    else:
        # Validate port is within reasonable range
        if not (1 <= port <= 65535):
            raise ValueError("Port must be between 1 and 65535")
    
    # Resolve the hostname
    try:
        ip_addresses = resolve_host(host)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname {host}: {e}")
    
    if not ip_addresses:
        raise ValueError(f"No IP addresses found for hostname {host}")
    
    # Build the full URL for the transport call (do not concatenate components)
    # We use the parsed components directly to ensure we don't build a URL string
    full_url = parsed._replace(port=port).geturl()
    
    # Call the transport
    status, headers, body = transport(full_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
