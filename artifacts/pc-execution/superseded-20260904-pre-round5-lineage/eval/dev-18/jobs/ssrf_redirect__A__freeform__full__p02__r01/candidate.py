import socket
import urllib.parse
from typing import Tuple, List

def fetch_text(url: str, transport, resolve_host: callable) -> str:
    """
    Fetch text from a URL using the provided transport and host resolution.
    
    Args:
        url: The URL to fetch (can be absolute or relative).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the scheme is not HTTP/HTTPS, status is not 200, or other disallowed conditions.
    """
    # Parse the URL to extract scheme, netloc, path, and query
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    hostname = parsed.netloc
    
    # Validate scheme: only HTTP and HTTPS are allowed
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # Determine the default port
    default_port = 80 if scheme == 'http' else 443
    
    # Ensure the hostname is present
    if not hostname:
        raise ValueError("URL must contain a hostname")
    
    # Resolve hostname to IP addresses
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not ip_addresses:
        raise ValueError(f"No IP addresses found for hostname: {hostname}")
    
    # Parse the path and query
    path = parsed.path
    query = parsed.query
    
    # Build the request URL with port if not specified
    if not parsed.port:
        request_url = f"{scheme}://{hostname}:{default_port}{path}"
        if query:
            request_url += f"?{query}"
    else:
        request_url = f"{scheme}://{hostname}:{parsed.port}{path}"
        if query:
            request_url += f"?{query}"
    
    # Make the request using the transport
    status, headers, body = transport(request_url)
    
    # Check the status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Return the body
    return body
