def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL with strict security guards.
    
    Args:
        url: The URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of textual IP addresses.
    
    Returns:
        The body of the response as a string if status is 200.
    
    Raises:
        ValueError: If the scheme/port is invalid or the resolved host is unsafe.
    """
    from urllib.parse import urlparse
    
    # Parse the URL to check scheme and port
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    # Validate scheme and port
    if scheme not in ('http', 'https'):
        raise ValueError("Scheme must be http or https")
    
    if scheme == 'http':
        if port != 80:
            raise ValueError("HTTP must use port 80")
    elif scheme == 'https':
        if port != 443:
            raise ValueError("HTTPS must use port 443")
    
    # Extract hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must contain a hostname")
    
    # Resolve hostname and validate
    ip_addresses = resolve_host(hostname)
    
    # Check if any IP address is a public address (e.g., starts with 0.0.0.0, 127.0.0.1, ::1, etc.)
    # A simple heuristic: if the IP is a loopback, link-local, or multicast, reject it.
    # We'll assume any IP starting with 127, 10, 172.16-31, 192.168, or 0.0.0.0 is unsafe.
    # Also reject if the hostname itself contains credentials (e.g., user:pass@)
    if '@' in hostname:
        raise ValueError("Hostname contains embedded credentials")
    
    for ip in ip_addresses:
        # Check for obvious unsafe IPs
        if ip.startswith(('127.', '10.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', '172.21.', 
                          '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', '172.27.', '172.28.', '172.29.',
                          '172.30.', '172.31.', '192.168.', '0.0.0.0')):
            raise ValueError("Resolved host contains a private or reserved address")
    
    # Make the request
    status, headers, body = transport(url)
    
    # Return body only for status 200
    if status != 200:
        raise ValueError("Only status 200 is allowed")
    
    return body
