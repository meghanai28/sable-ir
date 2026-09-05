def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL, following redirects up to 5 hops.
    
    Args:
        url: The URL to fetch (can be absolute or relative).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If the scheme or port is invalid or if DNS resolution fails.
    """
    # Parse the URL
    from urllib.parse import urlparse, urljoin
    
    parsed_url = urlparse(url)
    
    # Validate scheme and port
    valid_schemes = {'http', 'https'}
    if parsed_url.scheme not in valid_schemes:
        raise ValueError(f"Invalid scheme: {parsed_url.scheme}")
    
    default_ports = {'http': 80, 'https': 443}
    default_port = default_ports[parsed_url.scheme]
    
    # Resolve host
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("No hostname in URL")
    
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError(f"DNS resolution failed for {hostname}")
    
    # If no port specified, use default
    if not parsed_url.port:
        parsed_url = parsed_url._replace(port=default_port)
    
    # Check if port is valid for the scheme
    if parsed_url.port and parsed_url.port != default_port:
        # Allow non-default ports if they are valid integers and not 0
        if not isinstance(parsed_url.port, int) or parsed_url.port <= 0:
            raise ValueError(f"Invalid port: {parsed_url.port}")
    
    # Function to get the current URL for redirect following
    def get_current_url():
        return parsed_url.geturl()
    
    # Function to validate and update the URL
    def update_url(new_url_str):
        new_parsed = urlparse(new_url_str)
        
        # Check scheme
        if new_parsed.scheme not in valid_schemes:
            raise ValueError(f"Invalid scheme in redirect: {new_parsed.scheme}")
        
        # Check port
        if new_parsed.port:
            if new_parsed.port != default_ports[new_parsed.scheme]:
                raise ValueError(f"Invalid port in redirect: {new_parsed.port}")
        else:
            new_parsed = new_parsed._replace(port=default_ports[new_parsed.scheme])
        
        # Check hostname
        if not new_parsed.hostname:
            raise ValueError("No hostname in redirect URL")
        
        # Resolve host
        try:
            resolved_ips = resolve_host(new_parsed.hostname)
        except Exception:
            raise ValueError(f"DNS resolution failed for {new_parsed.hostname}")
        
        # Update parsed_url
        nonlocal parsed_url
        parsed_url = new_parsed
    
    # Parse the initial URL
    parsed_url = urlparse(url)
    
    # If no port specified, use default
    if not parsed_url.port:
        parsed_url = parsed_url._replace(port=default_port)
    
    # Follow redirects up to 5 hops
    max_hops = 5
    current_url = parsed_url.geturl()
    hops = 0
    
    while hops < max_hops:
        # Resolve host
        try:
            resolved_ips = resolve_host(parsed_url.hostname)
        except Exception:
            raise ValueError(f"DNS resolution failed for {parsed_url.hostname}")
        
        # Make the request
        status, headers, body = transport(current_url)
        
        # Check status
        if status != 200:
            # Check for Location header
            location_header = headers.get('Location')
            if location_header:
                # Join with current URL
                new_url = urljoin(current_url, location_header)
                update_url(new_url)
                hops += 1
                continue
            else:
                raise ValueError(f"Unexpected status code: {status}")
        
        # Return body
        return body
    
    raise ValueError(f"Too many redirects ({max_hops} hops)")
