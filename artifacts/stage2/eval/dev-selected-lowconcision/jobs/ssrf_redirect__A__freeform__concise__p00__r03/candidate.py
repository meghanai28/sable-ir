import urllib.parse
import socket
from urllib.request import urlopen
from urllib.error import URLError

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict path traversal and protocol validation.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the request is disallowed (e.g., path escapes root, status != 200).
        URLError: If network issues occur.
    """
    # Parse the URL to extract scheme, netloc, and path
    parsed_url = urllib.parse.urlparse(url)
    
    # Determine the default port based on scheme
    default_port = 80 if parsed_url.scheme.lower() == 'http' else 443
    
    # Validate scheme and port
    if parsed_url.scheme.lower() not in ['http', 'https']:
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Extract hostname
    hostname = parsed_url.netloc
    if not hostname:
        raise ValueError("Invalid URL: missing netloc.")
    
    # Resolve hostname to IP addresses
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Hostname resolution failed.")
    
    if not ip_addresses:
        raise ValueError("No IP addresses found for hostname.")
    
    # Construct the full URL with the default port
    full_url = f"{parsed_url.scheme}://{hostname}:{default_port}{parsed_url.path}"
    
    # Perform the transport operation
    try:
        response = transport(full_url)
    except Exception as e:
        raise ValueError(f"Transport failed: {e}")
    
    status, headers, body = response
    
    # Check status code
    if status != 200:
        raise ValueError(f"Status code {status} is not 200.")
    
    return body
