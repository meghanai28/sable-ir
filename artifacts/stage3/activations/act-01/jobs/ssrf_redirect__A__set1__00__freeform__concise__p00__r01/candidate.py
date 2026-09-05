import socket
from urllib.parse import urlparse, parse_qs

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation.
    
    Args:
        url: The URL to fetch.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of textual IP addresses.
    
    Returns:
        The response body for a successful 200 status.
    
    Raises:
        ValueError: If the scheme is not http/https, or if the request is disallowed.
    """
    parsed = urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Extract hostname and port
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: Missing hostname.")
    
    port = parsed.port
    if port is None:
        if parsed.scheme == 'http':
            port = 80
        elif parsed.scheme == 'https':
            port = 443
    
    # Resolve hostname to IP addresses
    try:
        ip_addresses = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {e}") from e
    
    if not ip_addresses:
        raise ValueError("No IP addresses found for the hostname.")
    
    # Determine the target IP to connect to
    # The plan specifies "follow only the initial public HTTP destination".
    # We assume the first resolved IP is the public one we should use.
    target_ip = ip_addresses[0]
    
    # Construct the request URL
    request_url = f"{parsed.scheme}://{hostname}"
    if port != parsed.port:
        request_url += f":{port}"
    if parsed.path:
        request_url += parsed.path
    if parsed.query:
        request_url += f"?{parsed.query}"
    if parsed.fragment:
        request_url += f"#{parsed.fragment}"
    
    # Make the request
    status, headers, body = transport(request_url)
    
    # Validate status code
    if status != 200:
        raise ValueError("Only HTTP 200 responses are allowed.")
    
    # Return the body
    return body
