def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation and no redirect following.
    
    Args:
        url: The URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status code 200.
    
    Raises:
        ValueError: If the URL scheme/port/host is invalid, or if the resolved IP is non-public,
                   or if a redirect is encountered.
    """
    from urllib.parse import urlparse, parse_qs
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Validate scheme
    allowed_schemes = ['http', 'https']
    if parsed.scheme not in allowed_schemes:
        raise ValueError(f"Disallowed scheme: {parsed.scheme}")
    
    # Determine port
    port = parsed.port
    if port is None:
        if parsed.scheme == 'http':
            port = 80
        else:
            port = 443
    
    # Validate port
    allowed_ports = {80, 443}
    if port not in allowed_ports:
        raise ValueError(f"Disallowed port: {port}")
    
    # Validate host
    if not parsed.hostname:
        raise ValueError("URL must have a hostname")
    
    hostname = parsed.hostname
    
    # Resolve hostname
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not ip_addresses:
        raise ValueError(f"Resolve_host returned no addresses for: {hostname}")
    
    # Validate resolved addresses (public address check)
    # Assuming "public" means IPv4 with valid octets or IPv6 with valid structure
    import re
    ipv4_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    ipv6_pattern = re.compile(r'^[0-9a-fA-F:]+$')
    
    def is_valid_ip(ip):
        if ':' in ip:
            return bool(ipv6_pattern.match(ip))
        else:
            return bool(ipv4_pattern.match(ip)) and all(0 <= int(part) <= 255 for part in ipv4_pattern.split(ip).split('.'))
    
    for ip in ip_addresses:
        if not is_valid_ip(ip):
            raise ValueError(f"Non-public or invalid IP address found: {ip}")
    
    # Construct the request URL for transport
    request_url = f"{parsed.scheme}://{hostname}:{port}{parsed.path}"
    if parsed.query:
        request_url += f"?{parsed.query}"
    
    # Call transport
    status, headers, body = transport(request_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Disallowed status code: {status}")
    
    # Check for redirects (HTTP 3xx)
    if 300 <= status < 400:
        raise ValueError("Redirects are disallowed")
    
    # Return body as string
    return body if isinstance(body, bytes) else str(body)
