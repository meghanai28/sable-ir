import urllib.parse
import socket
from typing import Tuple, Any

def fetch_text(url: str, transport: Any, resolve_host: Any) -> str:
    """
    Fetch text from a URL with strict validation.
    
    Args:
        url: The URL to fetch (absolute or relative).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: For disallowed schemes, ports, status codes, or malformed URLs.
    """
    # Parse the URL
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        raise ValueError("Malformed URL")
    
    scheme = parsed.scheme.lower()
    port = parsed.port
    path = parsed.path
    query = parsed.query
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Validate port
    if port is not None:
        if port != 80 and scheme == 'http':
            raise ValueError("Only default port 80 is allowed for HTTP")
        if port != 443 and scheme == 'https':
            raise ValueError("Only default port 443 is allowed for HTTPS")
    
    # Determine the host and port for the request
    host = parsed.hostname
    if not host:
        raise ValueError("URL must contain a hostname")
    
    if port is None:
        port = 80 if scheme == 'http' else 443
    
    # Check for malformed components
    if not path:
        path = '/'
    
    # Construct the request URL for the transport
    # We need to ensure the URL passed to transport matches our validation
    # The transport expects a URL that includes scheme, host, port, and path
    request_url = f"{scheme}://{host}:{port}{path}"
    if query:
        request_url += f"?{query}"
    
    # Call the transport
    status, headers, body = transport(request_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Status code {status} is not 200")
    
    # Return the body
    return body
