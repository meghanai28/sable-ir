import socket
import urllib.parse
from typing import Tuple, List, Any

def fetch_text(url: str, transport: Any, resolve_host: Any) -> str:
    """
    Fetch text from a URL, validating scheme and port, resolving host,
    and returning the body for a 200 status code.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If the scheme/port is invalid, status is not 200, or host resolution fails.
    """
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    # Validate scheme and port
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Validate port
    if port is None:
        if scheme == 'http':
            default_port = 80
        else:
            default_port = 443
        if port != default_port:
            raise ValueError(f"Only default ports are allowed for {scheme}.")
    else:
        if scheme == 'http' and port != 80:
            raise ValueError(f"Only default ports are allowed for {scheme}.")
        if scheme == 'https' and port != 443:
            raise ValueError(f"Only default ports are allowed for {scheme}.")
    
    # Resolve host
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL: missing hostname.")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Host resolution failed.")
    
    # Use the first valid IP address
    ip_address = ip_addresses[0]
    
    # Make the request
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Return body as text
    if isinstance(body, bytes):
        return body.decode('utf-8')
    else:
        return str(body)
