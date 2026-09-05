def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation and no redirect following.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the URL scheme/port/host is invalid, resolves to a non-public address,
                   or if a redirect is encountered.
    """
    import socket
    import urllib.parse
    
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname
    port = parsed.port
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # Determine expected port based on scheme
    if scheme == 'http':
        expected_port = 80
    else:
        expected_port = 443
    
    # Validate port: must be omitted (default) or exactly the expected port
    if port is not None and port != expected_port:
        raise ValueError(f"Port {port} is disallowed for {scheme} (expected {expected_port})")
    
    # Resolve hostname
    if not hostname:
        raise ValueError("Invalid hostname")
    
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not resolved_ips:
        raise ValueError(f"No public addresses found for: {hostname}")
    
    # Validate resolved addresses are public (not localhost or private)
    for ip in resolved_ips:
        if is_private_ip(ip):
            raise ValueError(f"Resolved address {ip} is not public")
    
    # Call transport
    status, headers, body = transport(url)
    
    # Check for redirect
    if 'location' in headers.lower() or 'location' in headers:
        raise ValueError("Redirects are disallowed")
    
    # Return body only for 200 status
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body


def is_private_ip(ip: str) -> bool:
    """
    Check if an IP address is private (localhost or private ranges).
    """
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    
    try:
        first_octet = int(parts[0])
        second_octet = int(parts[1])
        
        # Check for localhost (127.0.0.0/8)
        if first_octet == 127:
            return True
        
        # Check for link-local (169.254.0.0/16)
        if first_octet == 169 and second_octet == 254:
            return True
        
        # Check for private ranges
        # 10.0.0.0/8
        if first_octet == 10:
            return True
        
        # 172.16.0.0/12
        if first_octet == 172 and 16 <= second_octet <= 31:
            return True
        
        # 192.168.0.0/16
        if first_octet == 192 and second_octet == 168:
            return True
            
    except ValueError:
        return False
    
    return False
