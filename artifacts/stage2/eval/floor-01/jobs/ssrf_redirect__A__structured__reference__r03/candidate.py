def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body for a 200 status.
    
    Raises:
        ValueError: If the URL scheme/port/host is disallowed or the request fails validation.
    """
    # Parse the URL to check scheme and port
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    # Validate port
    if scheme == 'http':
        if port is not None and port != 80:
            raise ValueError("Disallowed port for HTTP")
    elif scheme == 'https':
        if port is not None and port != 443:
            raise ValueError("Disallowed port for HTTPS")
    
    # Extract hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("No hostname in URL")
    
    # Resolve hostname
    resolved_ips = resolve_host(hostname)
    if not resolved_ips:
        raise ValueError("Hostname resolution failed")
    
    # Validate public addresses
    for ip in resolved_ips:
        if not is_public_address(ip):
            raise ValueError("Non-public address detected")
    
    # Call transport
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError("Non-200 status code")
    
    return body


def is_public_address(ip: str) -> bool:
    """
    Check if an IP address is a public address.
    This is a simplified check; in a real scenario, a more comprehensive validation would be used.
    """
    # Block private IP ranges
    if ip.startswith(('127.', '10.', '192.168.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.', '0.')):
        return False
    
    # Block loopback
    if ip.startswith('::1'):
        return False
    
    # Block link-local
    if ip.startswith(('fe80:')):
        return False
    
    # Block multicast
    if ip.startswith(('ff00:')):
        return False
    
    return True
