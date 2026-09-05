def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict validation and redirect handling.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): Function(url) -> (status, headers, body) tuple.
        resolve_host (callable): Function(hostname) -> list of IP address strings.
    
    Returns:
        str: The body of the response for status 200.
    
    Raises:
        ValueError: If the scheme is not HTTP/HTTPS on default port, 
                    if hostname resolution fails, or if redirect constraints are violated.
    """
    from urllib.parse import urlparse, urljoin, urlunparse
    
    # Parse the initial URL
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    host = parsed.hostname
    path = parsed.path
    query = parsed.query
    
    # GUARD: Check scheme and port
    allowed_schemes = {'http', 'https'}
    allowed_ports = {'http': 80, 'https': 443}
    
    if scheme not in allowed_schemes:
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    if port is None:
        expected_port = allowed_ports[scheme]
        if port != expected_port:
            raise ValueError(f"Port mismatch: expected {expected_port}, got {port}")
    else:
        if port != allowed_ports[scheme]:
            raise ValueError(f"Port mismatch: expected {allowed_ports[scheme]}, got {port}")
    
    # GUARD: Resolve hostname
    if not resolve_host(host):
        raise ValueError(f"Failed to resolve hostname: {host}")
    
    # Track redirect history to prevent loops and ensure constraints
    # We will use the parsed components to check constraints
    current_scheme = scheme
    current_port = port
    current_host = host
    current_path = path
    current_query = query
    
    current_url = url
    
    # Follow redirects (at most 5)
    redirect_count = 0
    
    while True:
        # Make the request
        status, headers, body = transport(current_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"Request failed with status {status}")
        
        # Check for Location header (redirects)
        location_header = headers.get('location')
        
        if location_header:
            redirect_count += 1
            if redirect_count > 5:
                raise ValueError("Too many redirects")
            
            # Resolve the Location URL against the current URL
            # Note: In standard HTTP, the scheme, host, etc. are usually preserved,
            # but we must explicitly validate them as per the plan.
            try:
                new_parsed = urlparse(location_header)
            except Exception:
                raise ValueError(f"Invalid Location header format: {location_header}")
            
            # GUARD: Validate redirect constraints
            # Same scheme
            if new_parsed.scheme != current_scheme:
                raise ValueError(f"Redirect scheme mismatch: {new_parsed.scheme} != {current_scheme}")
            
            # Same port
            new_port = new_parsed.port
            if new_port is None:
                new_port = current_port
            if new_port != current_port:
                raise ValueError(f"Redirect port mismatch: {new_port} != {current_port}")
            
            # Same host (DNS) - The plan says "same ... DNS". 
            # Since we resolved the hostname to an IP, we compare the original hostnames.
            # However, the plan says "resolve the requested hostname and raise ValueError unless resolve_host returns at least one IP address".
            # For redirects, we compare the hostnames to ensure we stay on the same domain.
            if new_parsed.hostname != current_host:
                raise ValueError(f"Redirect hostname mismatch: {new_parsed.hostname} != {current_host}")
            
            # Same public address - We compare the resolved IP.
            # We need to resolve the new hostname and check if it matches the resolved old hostname.
            # Note: The plan says "resolve_host returns textual IP addresses".
            # We assume resolve_host returns the same set of IPs for the same hostname.
            new_ips = resolve_host(new_parsed.hostname)
            if not new_ips:
                raise ValueError(f"Failed to resolve new hostname: {new_parsed.hostname}")
            
            if set(new_ips) != set(resolve_host(current_host)):
                raise ValueError(f"Redirect DNS/IP mismatch: {new_parsed.hostname} != {current_host}")
            
            # Update current URL components
            current_scheme = new_parsed.scheme
            current_port = new_parsed.port
            current_host = new_parsed.hostname
            current_path = new_parsed.path
            current_query = new_parsed.query
            
            # Reconstruct the URL
            current_url = urlunparse((current_scheme, current_scheme + '://' + current_host, current_path, '', current_query))
        else:
            break
    
    return body
