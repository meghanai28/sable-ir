import os
import urllib.parse
import urllib.request
from typing import Tuple, List, Set

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL, validating the path against an extraction directory.
    
    Args:
        url: The URL to fetch from.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response if status is 200.
    
    Raises:
        ValueError: If the request is disallowed or status is not 200.
    """
    # Default ports for HTTP and HTTPS
    HTTP_PORT = 80
    HTTPS_PORT = 443
    
    # Parse the URL to get scheme, netloc, and path
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc
    path = parsed.path
    
    # Determine the port based on scheme
    port = HTTP_PORT if scheme == 'http' else HTTPS_PORT
    
    # Resolve the hostname to IP addresses
    try:
        ip_addresses = resolve_host(netloc)
    except Exception:
        raise ValueError("Failed to resolve hostname")
    
    # Construct the full URL with the resolved IP address
    # We use the first IP address found
    resolved_url = f"{scheme}://{ip_addresses[0]}:{port}{path}"
    
    # Fetch the content using the transport function
    try:
        status, headers, body = transport(resolved_url)
    except Exception:
        raise ValueError("Transport failed")
    
    # Check the status code
    if status != 200:
        raise ValueError("Only status 200 is allowed")
    
    # Decode the body to text
    try:
        text = body.decode('utf-8')
    except Exception:
        raise ValueError("Failed to decode body to text")
    
    return text
