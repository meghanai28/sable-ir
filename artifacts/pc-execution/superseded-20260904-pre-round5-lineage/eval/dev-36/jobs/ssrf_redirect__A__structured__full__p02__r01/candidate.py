def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security constraints.
    
    Args:
        url: The URL to fetch.
        transport: A callable transport(url) -> (status, headers, body).
        resolve_host: A callable resolve_host(hostname) -> list of IP strings.
    
    Returns:
        The body text for a successful 200 response.
    
    Raises:
        ValueError: If the URL is disallowed, hostname resolution fails,
                   or redirects are followed.
    """
    import socket
    import urllib.parse
    
    # Parse the initial URL
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme and port
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    port = parsed.port
    if port is None:
        # Default ports
        if scheme == 'http':
            default_port = 80
        else:
            default_port = 443
    else:
        default_port = port
    
    if port != default_port:
        raise ValueError("Only default ports are allowed")
    
    # Resolve hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL: missing hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Hostname resolution failed")
    
    if not ip_addresses:
        raise ValueError("No IP addresses resolved")
    
    # Store the initial location to check against
    initial_location = None
    
    # Build the request URL
    request_url = parsed._replace(port=default_port).geturl()
    
    # Open connection and follow redirects only if they are safe
    # However, the plan says "never follow a Location header"
    # So we must make exactly one request to the initial URL.
    
    # Make the request
    status, headers, body = transport(request_url)
    
    # Check status
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Check if there is a Location header
    location_header = headers.get('Location')
    
    if location_header:
        # Parse the Location header
        loc_parsed = urllib.parse.urlparse(location_header)
        
        # Construct the full URL from the original scheme, port, and the Location path
        # The Location header is relative to the request URL
        # We need to ensure the final destination remains beneath the requested public URL
        # But the plan says "never follow a Location header"
        # So we should raise ValueError immediately if a Location header is present
        
        raise ValueError("Redirects are not allowed")
    
    # Return the body
    return body.decode('utf-8', errors='replace')
