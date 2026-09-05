def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict security checks.
    
    Args:
        url: The URL to fetch (string).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the HTTP response as a string if status is 200.
    
    Raises:
        ValueError: If the scheme is not http/https, port is not default,
                   hostname cannot be resolved, or redirect destination fails checks.
    """
    from urllib.parse import urlparse, urljoin
    
    # Parse initial URL
    current_url = url
    parsed = urlparse(current_url)
    
    # Validate scheme and port
    valid_schemes = {'http', 'https'}
    if parsed.scheme not in valid_schemes:
        raise ValueError(f"Invalid scheme: {parsed.scheme}")
    
    # Determine expected default port
    default_port = {'http': 80, 'https': 443}[parsed.scheme]
    
    # Check if port is default
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError(f"Non-default port {parsed.port} not allowed")
    
    # Resolve and check hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid hostname in URL")
    
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Cannot resolve hostname: {hostname}")
    
    if not resolved_ips:
        raise ValueError(f"No IP addresses resolved for: {hostname}")
    
    # State for redirect following
    max_redirects = 5
    redirect_count = 0
    
    while True:
        # Get response
        status, headers, body = transport(current_url)
        
        # Check status
        if status != 200:
            raise ValueError(f"Request failed with status {status}")
        
        # Check for Location header (redirects)
        location_header = headers.get('Location')
        
        if location_header:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError(f"Too many redirects ({redirect_count})")
            
            # Resolve relative URL against current URL
            new_url = urljoin(current_url, location_header)
            new_parsed = urlparse(new_url)
            
            # Security checks for redirect
            # 1. Same scheme and port as initial request
            if new_parsed.scheme != parsed.scheme:
                raise ValueError(f"Redirect changes scheme to {new_parsed.scheme}")
            
            if new_parsed.port is not None:
                if new_parsed.port != default_port:
                    raise ValueError(f"Redirect uses non-default port {new_parsed.port}")
            
            # 2. No .. segments in path
            if '..' in new_parsed.path:
                raise ValueError("Redirect contains '..' segments")
            
            # Update current URL
            current_url = new_url
            parsed = urlparse(current_url)
            continue
        else:
            break
    
    return body
