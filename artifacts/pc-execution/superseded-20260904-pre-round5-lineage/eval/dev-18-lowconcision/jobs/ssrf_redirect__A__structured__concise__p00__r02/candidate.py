import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL.
    
    Args:
        url: The URL to fetch from.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body text of the initial request's 200 response.
    
    Raises:
        ValueError: If the request is disallowed (e.g., non-HTTP/HTTPS, non-default port, or resolution fails).
    """
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # Check scheme
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Check port (default for HTTP is 80, HTTPS is 443)
    port = parsed.port
    if port is None:
        if scheme == 'http':
            port = 80
        else:
            port = 443
    
    # Validate port
    if port != 80 and port != 443:
        raise ValueError("Only default ports (80 for HTTP, 443 for HTTPS) are allowed.")
    
    # Resolve hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL: missing hostname.")
    
    # Resolve the hostname
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not resolved_ips:
        raise ValueError(f"No IP addresses found for hostname: {hostname}")
    
    # Use the first resolved IP for the request
    ip_address = resolved_ips[0]
    
    # Construct the full URL with the resolved IP
    # Note: We do not follow redirects. We only use the initial destination.
    # If the URL has a path, we use it. If not, we use the scheme://ip.
    if parsed.path:
        full_url = f"{scheme}://{ip_address}{parsed.path}"
    else:
        full_url = f"{scheme}://{ip_address}"
    
    # Parse the final URL to ensure we have the correct path and query
    final_parsed = urllib.parse.urlparse(full_url)
    
    # Create a request object
    req = urllib.request.Request(final_parsed.geturl())
    
    # Use the transport function
    try:
        status, headers, body = transport(url)
    except Exception as e:
        raise ValueError(f"Transport error: {e}")
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Decode the body to text
    if isinstance(body, bytes):
        return body.decode('utf-8')
    else:
        return body
