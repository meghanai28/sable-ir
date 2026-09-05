def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security guards.
    
    Args:
        url: The URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response if status is 200.
    
    Raises:
        ValueError: If the request is disallowed (e.g., non-HTTP/HTTPS, non-finite IPs).
    """
    # Parse the URL to get scheme, netloc, and path
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    
    # Guard: Accept only HTTP or HTTPS on the default port
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    port = parsed.port
    default_port = 80 if scheme == 'http' else 443
    
    if port is not None and port != default_port:
        raise ValueError("Only default ports are allowed.")
    
    # Guard: Resolve the hostname
    hostname = parsed.netloc
    if not hostname:
        raise ValueError("Invalid URL: missing netloc.")
    
    # Guard: Resolve host and check for finite IPs
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Failed to resolve hostname.")
    
    for ip in ip_addresses:
        if not ip or not ip.isfinite():
            raise ValueError("Resolved IP addresses must be finite.")
    
    # Guard: Follow the initial destination only, do not follow redirects
    # We use the original parsed URL for the request, ignoring any redirect in the response
    request_url = url
    
    # Call transport to get the response
    status, headers, body = transport(request_url)
    
    # Guard: Return the body for status 200
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
