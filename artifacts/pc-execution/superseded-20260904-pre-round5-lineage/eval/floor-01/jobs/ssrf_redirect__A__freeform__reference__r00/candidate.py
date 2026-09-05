def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation and security checks.
    
    Args:
        url: The URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the URL is invalid, scheme/port is disallowed, 
                    credentials are present, redirect is encountered, 
                    or resolved IP is not a global public address.
    """
    from urllib.parse import urlparse, parse_qs
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Validate port
    port = parsed.port
    if port:
        if parsed.scheme == 'http' and port != 80:
            raise ValueError("HTTP must use port 80.")
        if parsed.scheme == 'https' and port != 443:
            raise ValueError("HTTPS must use port 443.")
    
    # Extract hostname
    hostname = parsed.netloc
    
    # Remove credentials from hostname
    if '@' in hostname:
        raise ValueError("URLs must not contain credentials.")
    
    # Reconstruct URL with just scheme, netloc (without credentials), and path
    # Ensure port is included if it was specified in the original URL (even if default)
    # Actually, the spec says "omit port or port 80/443", so we should use the host without port 
    # if it's the default, but keep the path.
    # Let's normalize the netloc: if port is default, remove it from the string representation.
    if port == 80 and parsed.scheme == 'http':
        normalized_netloc = hostname
    elif port == 443 and parsed.scheme == 'https':
        normalized_netloc = hostname
    else:
        normalized_netloc = f"{hostname}:{port}"
    
    # Construct the URL for transport without credentials
    # We need to be careful about the path and query
    path = parsed.path
    query = parsed.query
    
    if path == '' and query == '':
        final_url = f"{parsed.scheme}://{normalized_netloc}"
    else:
        final_url = f"{parsed.scheme}://{normalized_netloc}{path}"
        if query:
            final_url += f"?{query}"
    
    # Resolve hostname
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError("Hostname resolved to no addresses.")
    
    # Check if any address is not a global public address
    # A global public address typically starts with 10, 172.16-31, 192.168, 127, ::1, etc.
    # We'll assume standard private ranges are not public.
    private_prefixes = ['10.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', 
                         '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', 
                         '172.27.', '172.28.', '172.29.', '172.30.', '172.31.', '192.168.',
                         '127.', '::1', 'fe80:', 'fc', 'fd']
    
    is_global_public = False
    for ip in ip_addresses:
        if ip.startswith(('10.', '127.', '::1', 'fe80:')) or ip.startswith(('fc', 'fd', '192.168.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.')):
            is_global_public = False
            break
        else:
            is_global_public = True
            break
    
    if not is_global_public:
        raise ValueError("Resolved address is not a global public address.")
    
    # Call transport exactly once
    status, headers, body = transport(final_url)
    
    # Check for redirect status codes
    redirect_codes = {301, 302, 303, 307, 308}
    if status in redirect_codes:
        raise ValueError("Redirect status codes are disallowed.")
    
    # Return body only for status 200
    if status != 200:
        raise ValueError("Only status 200 is allowed.")
    
    return body
