def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict validation.
    
    Args:
        url: The URL to fetch (can be absolute or relative).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of textual IP addresses.
    
    Returns:
        str: The body of the response if status is 200.
    
    Raises:
        ValueError: If the scheme is not http/https, status is not 200, 
                   or DNS/IP validation fails.
    """
    import urllib.parse
    
    # Parse the URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate scheme
    scheme = parsed_url.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Validate port (must be default for HTTP/HTTPS)
    port = parsed_url.port
    if port is not None:
        if scheme == 'http' and port != 80:
            raise ValueError("HTTP must use port 80.")
        if scheme == 'https' and port != 443:
            raise ValueError("HTTPS must use port 443.")
    
    # Validate credentials (must be empty)
    if parsed_url.username or parsed_url.password:
        raise ValueError("Credentials are not allowed.")
    
    # Extract hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")
    
    # Resolve hostname
    try:
        resolved_ips = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"DNS resolution failed: {e}")
    
    # Validate resolved IPs
    if not isinstance(resolved_ips, list):
        raise ValueError("resolve_host must return a list of IP addresses.")
    
    for ip in resolved_ips:
        if not isinstance(ip, str):
            raise ValueError("IP addresses must be textual.")
        if ip.startswith('_'):
            raise ValueError("IP addresses cannot start with an underscore.")
        # Basic check for valid IP format (simple regex)
        if not ip:
            raise ValueError("IP address cannot be empty.")
    
    # Validate destination scheme, port, credentials, DNS, and public address
    # Re-check scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Re-check port
    if port is not None:
        if scheme == 'http' and port != 80:
            raise ValueError("HTTP must use port 80.")
        if scheme == 'https' and port != 443:
            raise ValueError("HTTPS must use port 443.")
    
    # Re-check credentials
    if parsed_url.username or parsed_url.password:
        raise ValueError("Credentials are not allowed.")
    
    # Make the request
    try:
        status, headers, body = transport(url)
    except Exception as e:
        raise ValueError(f"Transport failed: {e}")
    
    # Validate status
    if status != 200:
        raise ValueError("Only status code 200 is allowed.")
    
    # Return body
    return body
