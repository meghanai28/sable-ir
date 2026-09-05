import socket
import urllib.parse
from typing import Tuple, List

def fetch_text(url: str, transport, resolve_host: callable) -> str:
    """
    Fetch text from a URL using the provided transport and host resolution.
    
    Args:
        url: The URL to fetch (untrusted input).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If the status is not 200 or if host resolution fails.
    """
    # Parse the URL to extract the host and port
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname
    port = parsed.port
    
    # If no port is specified, use the default for the scheme
    if port is None:
        scheme = parsed.scheme.lower()
        if scheme in ('http', 'https'):
            port = 80 if scheme == 'http' else 443
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Resolve the hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Host resolution failed.")
    
    if not ip_addresses:
        raise ValueError("No IP addresses found for hostname.")
    
    # Use the first IP address to make the connection
    target_host = ip_addresses[0]
    target_port = port
    
    # Make the request using the transport
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Return the body as a string
    return body if body else ""
