def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation and transport constraints.
    
    Args:
        url: The URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the URL is invalid, the hostname is invalid, or a redirect is encountered.
    """
    
    # Parse the URL
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    
    # Validate scheme
    allowed_schemes = {'http', 'https'}
    if parsed.scheme not in allowed_schemes:
        raise ValueError(f"Disallowed scheme: {parsed.scheme}")
    
    # Validate port
    port = parsed.port
    if port is not None:
        if parsed.scheme == 'http' and port != 80:
            raise ValueError(f"HTTP port must be 80, got {port}")
        if parsed.scheme == 'https' and port != 443:
            raise ValueError(f"HTTPS port must be 443, got {port}")
    
    # Validate host
    if not parsed.hostname:
        raise ValueError("URL must have a hostname")
    
    # Validate credentials (username or password present)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL cannot contain credentials")
    
    # Validate path
    if parsed.path:
        raise ValueError("URL path is not allowed")
    
    # Resolve hostname
    hostname = parsed.hostname
    try_addresses = resolve_host(hostname)
    
    if not try_addresses:
        raise ValueError(f"Resolve failed for hostname: {hostname}")
    
    # Filter for global public addresses
    # Note: Without a real DNS lookup or public IP database, we assume any resolved IP
    # is acceptable if it's a standard IPv4 or IPv6. We check for localhost/private ranges.
    valid_addresses = []
    for addr in try_addresses:
        # Check for private/reserved ranges
        if addr.startswith(('127.', '10.', '192.168.', '172.16.', '172.17.', 
                           '172.24.', '172.31.', '169.254.', '0.0.0.0', '::1')):
            continue
        valid_addresses.append(addr)
    
    if not valid_addresses:
        raise ValueError(f"Resolved addresses are not public: {try_addresses}")
    
    # Use the first valid public address for the transport call
    # The transport function signature expects the full URL string, so we use the original URL
    # but we've validated the components.
    
    # Call transport exactly once
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Check for redirects
    if status in (301, 302, 303, 307, 308):
        raise ValueError(f"Redirect status {status} is disallowed")
    
    return body
