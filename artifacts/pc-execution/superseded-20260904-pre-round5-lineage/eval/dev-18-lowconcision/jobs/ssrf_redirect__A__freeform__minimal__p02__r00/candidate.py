import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL with strict scheme/port validation and no redirect following.
    
    Args:
        url: The URL to fetch (absolute or relative).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response for a 200 status code.
    
    Raises:
        ValueError: If the scheme or port is not HTTP (80) or HTTPS (443).
    """
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f"Unsupported scheme: {parsed.scheme}")
    
    # Validate port
    port = parsed.port
    if port is None:
        if parsed.scheme == 'http':
            port = 80
        elif parsed.scheme == 'https':
            port = 443
    else:
        if parsed.scheme == 'http' and port != 80:
            raise ValueError(f"HTTP port must be 80, got {port}")
        if parsed.scheme == 'https' and port != 443:
            raise ValueError(f"HTTPS port must be 443, got {port}")
    
    # Resolve host
    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"Invalid URL: missing hostname in {url}")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError(f"Could not resolve hostname: {hostname}")
    
    # Construct the full URL for transport
    # Ensure the path is absolute if provided
    if parsed.path:
        full_url = f"{parsed.scheme}://{hostname}:{port}{parsed.path}"
    else:
        full_url = f"{parsed.scheme}://{hostname}:{port}"
    
    # Call transport
    status, headers, body = transport(full_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Return body as string
    return body if body else ""
