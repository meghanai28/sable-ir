import socket
import urllib.parse
from typing import Tuple, List, Any


def fetch_text(url: str, transport: Any, resolve_host: Any) -> str:
    """
    Fetch text from a URL using the provided transport and host resolver.
    
    Args:
        url: The URL to fetch from.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string if the status code is 200.
    
    Raises:
        ValueError: If the URL scheme is not HTTP or HTTPS, or if the status code is not 200.
    """
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate scheme
    scheme = parsed_url.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Validate port
    port = parsed_url.port
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
    else:
        if scheme == 'http' and port != 80:
            raise ValueError("HTTP requests must be on port 80.")
        if scheme == 'https' and port != 443:
            raise ValueError("HTTPS requests must be on port 443.")
    
    # Resolve hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("URL must have a valid hostname.")
    
    try:
        ips = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not ips:
        raise ValueError(f"No IP addresses found for hostname: {hostname}")
    
    # Use the first resolved IP
    target_ip = ips[0]
    
    # Construct the full URL for the transport function
    full_url = parsed_url._replace(port=port, scheme=scheme).geturl()
    
    # Call the transport function
    status, headers, body = transport(full_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Request failed with status code: {status}")
    
    return body
