def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation and redirect handling.
    
    Args:
        url: The URL to fetch (untrusted input).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns textual IP addresses.
    
    Returns:
        The body of the HTTP response if status is 200.
    
    Raises:
        ValueError: If the scheme is not http/https, or if any redirect destination
                    is out of bounds (not reachable via the initial resolution).
    """
    # Validate scheme
    if not url.startswith("http://") and not url.startswith("https://"):
        raise ValueError("Only http and https schemes are allowed")
    
    # Resolve the initial hostname
    initial_host = url.split("://")[1].split("/")[0]
    try:
        resolved_ips = resolve_host(initial_host)
    except Exception:
        raise ValueError("Failed to resolve hostname")
    
    if not resolved_ips:
        raise ValueError("No IP addresses resolved for hostname")
    
    current_url = url
    
    # Follow redirects (at most 5)
    redirect_count = 0
    while redirect_count < 5:
        # Parse current URL
        scheme = current_url.split("://")[0]
        path = current_url.split("://")[1].split("/")[0]
        
        # Construct the request URL for transport
        request_url = f"{scheme}://{path}"
        
        # Get response
        status, headers, body = transport(request_url)
        
        # Check status
        if status != 200:
            raise ValueError("Unexpected HTTP status code")
        
        # Check for Location header
        location_header = headers.get("Location")
        if location_header:
            redirect_count += 1
            if redirect_count >= 5:
                raise ValueError("Too many redirects")
            
            # Resolve the new URL
            new_url = location_header
            
            # Validate scheme
            if not new_url.startswith("http://") and not new_url.startswith("https://"):
                raise ValueError("Redirect URL must have http or https scheme")
            
            # Resolve the new hostname
            new_host = new_url.split("://")[1].split("/")[0]
            try:
                resolved_ips = resolve_host(new_host)
            except Exception:
                raise ValueError("Failed to resolve redirect hostname")
            
            if not resolved_ips:
                raise ValueError("No IP addresses resolved for redirect hostname")
            
            # Check if the new URL is within bounds (reachable via initial resolution)
            # This means the new URL's IP must be one of the resolved IPs from the initial hostname
            # However, since we can't know the final IP before resolution, we check if the host
            # is reachable via the same DNS resolution process (same set of IPs)
            # Actually, the requirement says "keeping scheme, port, credentials, DNS, and public address validation exactly as for the initial destination"
            # This implies we should check if the new host resolves to the same IP set as the initial host
            if set(resolved_ips) != set(initial_resolved_ips):
                raise ValueError("Redirect destination is out of bounds")
            
            current_url = new_url
        else:
            break
    
    return body
