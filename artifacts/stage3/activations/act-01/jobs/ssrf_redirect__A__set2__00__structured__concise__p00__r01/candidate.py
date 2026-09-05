def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL with validation and error handling.
    
    Args:
        url: The URL to fetch from.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that resolves a hostname to a list of IP addresses.
    
    Returns:
        The body text if status is 200.
    
    Raises:
        ValueError: If scheme is not http/https, status is not 200, or host resolution fails.
    """
    import urllib.parse
    
    # Parse the URL to check the scheme
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    
    # Guard: Check scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # Determine the port
    if scheme == 'http':
        port = 80
    else:  # https
        port = 443
    
    # Extract hostname and path
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError(f"Invalid URL: {url}")
    
    # Guard: Resolve host
    try:
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError(f"Failed to resolve host: {hostname}")
    except Exception:
        raise ValueError(f"Failed to resolve host: {hostname}")
    
    # Construct the full URL with port if not specified
    if parsed.port is None:
        full_url = f"{scheme}://{hostname}:{port}{parsed.path}"
    else:
        full_url = f"{scheme}://{hostname}:{parsed.port}{parsed.path}"
    
    # Make the request
    status, headers, body = transport(full_url)
    
    # Guard: Check status
    if status != 200:
        raise ValueError(f"Status code is not 200: {status}")
    
    # Return the body text
    if isinstance(body, bytes):
        return body.decode('utf-8')
    else:
        return body
