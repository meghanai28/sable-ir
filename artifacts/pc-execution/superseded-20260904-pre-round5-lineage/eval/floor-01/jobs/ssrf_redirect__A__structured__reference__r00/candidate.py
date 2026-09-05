def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation and limited transport.
    
    Args:
        url: The URL to fetch.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of textual IP addresses.
    
    Returns:
        The response body for a 200 status.
    
    Raises:
        ValueError: If the URL is invalid, disallowed scheme/port, or host resolves to non-public.
    """
    from urllib.parse import urlparse, parse_qs
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Guard: Check for disallowed schemes
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    # Guard: Check for credentials (username or password)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL contains credentials")
    
    # Guard: Check port and scheme requirements
    # HTTP must be port 80 or omitted
    # HTTPS must be port 443 or omitted
    allowed_ports = {'http': 80, 'https': 443}
    scheme = parsed.scheme
    port = parsed.port
    
    if scheme == 'http':
        if port not in [None, 80]:
            raise ValueError("HTTP must use port 80 or be omitted")
    elif scheme == 'https':
        if port not in [None, 443]:
            raise ValueError("HTTPS must use port 443 or be omitted")
    
    # Guard: Validate hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("No hostname in URL")
    
    # Resolve hostname
    addresses = resolve_host(hostname)
    if not addresses:
        raise ValueError("Host resolves to no addresses")
    
    # Guard: Check if any address is not a global public address
    # Assuming "global public" means not a link-local, loopback, or multicast
    # Common non-public ranges: 127.0.0.0/8, ::1, fe80::/10, etc.
    import re
    # Regex for IPv4 private ranges and IPv6 private ranges
    private_ipv4_pattern = re.compile(r'^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|169\.254\.|0\.)')
    private_ipv6_pattern = re.compile(r'^(::1|fe80::|fc00::|::1)')
    
    for addr in addresses:
        if isinstance(addr, str):
            if re.match(private_ipv4_pattern, addr) or re.match(private_ipv6_pattern, addr):
                raise ValueError("Non-public address")
    
    # Call transport exactly once
    status, headers, body = transport(url)
    
    # Guard: Check status code
    if status != 200:
        raise ValueError("Unexpected status code")
    
    # Guard: Check for redirects (301, 302, 303, 307, 308)
    # The problem states to raise ValueError for redirect status without following, even if destination looks public.
    # Since we call transport exactly once, we assume the URL given is the final one or we don't follow redirects.
    # However, the spec says "after the first response, treat any redirect status ... as disallowed and raise ValueError without following".
    # Since we only call transport once, we just check the status of that single call.
    # If the status is a redirect, we raise ValueError.
    if status in [301, 302, 303, 307, 308]:
        raise ValueError("Redirect status not allowed")
    
    return body
