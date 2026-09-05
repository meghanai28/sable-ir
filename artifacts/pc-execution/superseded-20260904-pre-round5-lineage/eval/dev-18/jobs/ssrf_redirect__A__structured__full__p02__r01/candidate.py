def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security controls.
    
    Args:
        url: The URL to fetch.
        transport: A callable transport(url) -> (status, headers, body).
        resolve_host: A callable resolve_host(hostname) -> list of textual IP addresses.
    
    Returns:
        The body of the response for status 200.
    
    Raises:
        ValueError: For disallowed schemes, invalid host resolutions, or redirects.
    """
    import socket
    from urllib.parse import urlparse, unquote
    
    # Parse the URL to determine scheme and netloc
    parsed = urlparse(url)
    
    # Validate scheme: only HTTP or HTTPS on default ports
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    port = parsed.port
    if port is None:
        port = 80 if scheme == 'http' else 443
    
    # Resolve the hostname
    netloc = parsed.netloc
    if not netloc:
        raise ValueError("Invalid URL: missing netloc.")
    
    # Remove port if present for resolution, then resolve
    if ':' in netloc:
        hostname, _ = netloc.rsplit(':', 1)
    else:
        hostname = netloc
    
    if not resolve_host(hostname):
        raise ValueError("Hostname resolution failed.")
    
    # Construct the full URL for transport
    full_url = url
    
    # Fetch the response
    status, headers, body = transport(full_url)
    
    # Check for 3xx redirects
    if status >= 300 and status < 400:
        raise ValueError("Redirects are not allowed.")
    
    # Check status code
    if status != 200:
        raise ValueError(f"Expected status 200, got {status}.")
    
    return body
