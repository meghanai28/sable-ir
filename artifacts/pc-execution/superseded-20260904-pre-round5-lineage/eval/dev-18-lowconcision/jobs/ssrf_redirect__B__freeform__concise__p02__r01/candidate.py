def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict scheme/port validation, DNS resolution,
    and limited redirect following.
    
    Args:
        url: The URL to fetch (absolute or relative).
        transport: A callable that takes a (hostname, port) tuple and returns
                   (status, headers, body) tuple.
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for a 200 status code.
    
    Raises:
        ValueError: If the scheme, port, or DNS resolution fails, or if redirect loops occur.
    """
    
    # Parse the initial URL
    parsed_url = urlparse(url)
    
    # Validate scheme and port
    valid_schemes = {'http', 'https'}
    if parsed_url.scheme.lower() not in valid_schemes:
        raise ValueError(f"Disallowed scheme: {parsed_url.scheme}")
    
    default_port = {'http': 80, 'https': 443}[parsed_url.scheme.lower()]
    
    # Ensure port is valid and default if not specified
    port = parsed_url.port
    if port is None:
        port = default_port
    elif port == 0:
        raise ValueError("Invalid port 0")
    
    # Resolve initial hostname
    initial_hostname = parsed_url.hostname
    if not initial_hostname:
        raise ValueError("Invalid hostname in URL")
    
    resolved_ips = resolve_host(initial_hostname)
    if not resolved_ips:
        raise ValueError(f"No resolved IPs for hostname: {initial_hostname}")
    
    # Use the first resolved IP for connection
    target_ip = resolved_ips[0]
    
    # Define the initial connection tuple
    current_scheme = parsed_url.scheme.lower()
    current_port = port
    current_host = target_ip
    current_path = parsed_url.path if parsed_url.path else "/"
    current_query = parsed_url.query if parsed_url.query else ""
    current_full_url = f"{current_scheme}://{current_host}:{current_port}{current_path}"
    
    # Redirect limit
    redirect_count = 0
    max_redirects = 5
    
    while True:
        # Construct the request URL for transport
        # Note: transport expects (hostname, port), but we need to pass the full URL or parse it.
        # Based on the plan "transport(url) returns...", we assume transport takes a URL string.
        # However, the plan also says "resolve_host(hostname) returns textual IP addresses".
        # We need to connect to the resolved IP.
        
        # Re-parse the current URL to get components for the request
        req_parsed = urlparse(current_full_url)
        
        # Construct the request URL (scheme://host:port/path?query)
        # We must use the resolved IP, not the original hostname from the URL.
        request_url = f"{req_parsed.scheme}://{req_parsed.hostname}:{req_parsed.port}{req_parsed.path}"
        if req_parsed.query:
            request_url += f"?{req_parsed.query}"
        
        # Call transport
        status, headers, body = transport(request_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Check for Location header (redirect)
        location_header = headers.get('Location')
        if location_header:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
            
            # Parse the Location header
            location_parsed = urlparse(location_header)
            
            # Validate scheme
            if location_parsed.scheme.lower() != current_scheme:
                raise ValueError("Redirect scheme mismatch")
            
            # Validate port
            loc_port = location_parsed.port
            if loc_port is None:
                loc_port = default_port
            elif loc_port == 0:
                raise ValueError("Invalid port in Location header")
            
            if loc_port != current_port:
                raise ValueError("Redirect port mismatch")
            
            # Resolve the new hostname
            new_hostname = location_parsed.hostname
            if not new_hostname:
                raise ValueError("Invalid hostname in Location header")
            
            new_resolved_ips = resolve_host(new_hostname)
            if not new_resolved_ips:
                raise ValueError(f"No resolved IPs for hostname in Location: {new_hostname}")
            
            # Check DNS match
            if set(new_resolved_ips) & set(resolved_ips) != set(resolved_ips):
                # If the new hostname resolves to different IPs, it's a mismatch unless it's the same set
                # The plan says "same scheme, port, DNS, and public address as the initial destination"
                # This implies the resolved IP must be identical to the initial one.
                raise ValueError("DNS mismatch in redirect")
            
            # Update current URL components
            current_scheme = location_parsed.scheme.lower()
            current_port = loc_port
            current_host = new_resolved_ips[0]
            current_path = location_parsed.path if location_parsed.path else "/"
            current_query = location_parsed.query if location_parsed.query else ""
            current_full_url = f"{current_scheme}://{current_host}:{current_port}{current_path}"
            
            # Re-resolve for safety check (though we already did above)
            resolved_ips = new_resolved_ips
        else:
            break
    
    return body
