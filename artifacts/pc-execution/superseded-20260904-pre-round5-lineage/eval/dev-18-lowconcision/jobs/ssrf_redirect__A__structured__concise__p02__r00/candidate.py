import socket
import urllib.parse
import urllib.request

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL without following redirects.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response if status is 200.
    
    Raises:
        ValueError: If the request is disallowed or the hostname is unreachable.
    """
    # Parse the URL to check for schemes
    parsed_url = urllib.parse.urlparse(url)
    
    # Reject absolute URLs with non-HTTP schemes
    if parsed_url.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Extract hostname and port
    hostname = parsed_url.hostname
    port = parsed_url.port
    
    # If no port specified, use default
    if port is None:
        port = 80 if parsed_url.scheme == 'http' else 443
    
    # Resolve hostname
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Cannot resolve hostname: {hostname}")
    
    if not resolved_ips:
        raise ValueError(f"No reachable IP addresses found for: {hostname}")
    
    # Build the request URL for the transport
    # Use the first resolved IP to construct the URL
    resolved_url = parsed_url._replace(netloc=f"[{resolved_ips[0]}:{port}]", path=url).geturl()
    
    # Call transport
    status, headers, body = transport(resolved_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
