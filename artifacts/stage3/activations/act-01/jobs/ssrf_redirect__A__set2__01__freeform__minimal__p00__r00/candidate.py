import socket
import urllib.parse
import urllib.request
import urllib.error
import ssl
from typing import Tuple, List, Optional

def resolve_host(hostname: str) -> List[str]:
    """Resolve hostname to a list of IP addresses."""
    try:
        return socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"Failed to resolve hostname: {hostname}")

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL using the provided transport.
    
    Args:
        url: The URL to fetch from (treated as untrusted input).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns IP addresses.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If status is not 200 or if hostname resolution fails.
    """
    # Parse the URL to extract the netloc (hostname) and path
    parsed_url = urllib.parse.urlparse(url)
    hostname = parsed_url.netloc
    
    # Resolve the hostname to IP addresses
    try:
        ip_addresses = resolve_host(hostname)
    except ValueError:
        raise ValueError(f"Invalid hostname or resolution failed: {hostname}")
    
    if not ip_addresses:
        raise ValueError(f"No IP addresses found for: {hostname}")
    
    # Determine the default port based on the scheme
    scheme = parsed_url.scheme.lower()
    default_port = None
    if scheme == "http":
        default_port = 80
    elif scheme == "https":
        default_port = 443
    else:
        raise ValueError(f"Unsupported scheme: {scheme}")
    
    # Construct the target URL using the resolved host and default port
    # We do not concatenate components; we rebuild the URL from parsed parts
    target_url = f"{scheme}://{hostname}"
    if default_port is not None:
        target_url += f":{default_port}"
    
    # Append the path and query from the original URL
    if parsed_url.path:
        target_url += parsed_url.path
    if parsed_url.query:
        target_url += f"?{parsed_url.query}"
    
    # Use the transport to fetch the data
    status, headers, body = transport(target_url)
    
    # Check if the status code is exactly 200
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
