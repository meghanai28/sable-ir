def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict security checks.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): Function to fetch HTTP response.
        resolve_host (callable): Function to resolve hostname to IP addresses.
    
    Returns:
        str: The body of the HTTP response.
    
    Raises:
        ValueError: If the request is disallowed (wrong scheme/port, 
                   no valid IPs, bad redirect, non-200 status).
    """
    # Parse the initial URL
    parsed = urlparse(url)
    scheme = parsed.scheme
    host = parsed.hostname
    port = parsed.port
    path = parsed.path
    query = parsed.query
    # Default ports for HTTP/HTTPS
    default_port = {
        'http': 80,
        'https': 443
    }
    # Check scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    # Check port
    if port is None:
        port = default_port[scheme]
    if port != default_port[scheme]:
        raise ValueError(f"Non-default port {port} for scheme {scheme}")
    
    # Resolve host
    ips = resolve_host(host)
    if not ips:
        raise ValueError("resolve_host returned no IPs")
    
    # Initial request
    current_url = url
    max_redirects = 5
    redirect_count = 0
    
    while True:
        # Prepare the request URL
        # If we are in a redirect, we need to use the full URL with scheme and port
        # The transport expects a full URL
        if redirect_count > 0:
            # Reconstruct URL with scheme and port
            if port is None:
                port = default_port[scheme]
            new_url = f"{scheme}://{host}:{port}{path}?{query}"
        else:
            new_url = current_url
        
        # Make request
        status, headers, body = transport(new_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"Status code {status} is not 200")
        
        # Check for redirects
        if 'Location' in headers:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError(f"Too many redirects ({redirect_count})")
            
            location = headers['Location']
            
            # Parse redirect URL
            redirect_parsed = urlparse(location)
            redirect_scheme = redirect_parsed.scheme
            redirect_host = redirect_parsed.hostname
            redirect_port = redirect_parsed.port
            
            # Check scheme
            if redirect_scheme not in ('http', 'https'):
                raise ValueError(f"Redirect to disallowed scheme: {redirect_scheme}")
            
            # Check for javascript: or data:
            if redirect_scheme in ('javascript:', 'data:'):
                raise ValueError(f"Redirect to {redirect_scheme} URL")
            
            # Check port
            if redirect_port is None:
                redirect_port = default_port[redirect_scheme]
            if redirect_port != default_port[redirect_scheme]:
                raise ValueError(f"Redirect to non-default port {redirect_port}")
            
            # Resolve new host
            new_ips = resolve_host(redirect_host)
            if not new_ips:
                raise ValueError("resolve_host returned no IPs for redirect host")
            
            # Update current URL
            path = redirect_parsed.path
            query = redirect_parsed.query
            current_url = f"{redirect_scheme}://{redirect_host}:{redirect_port}{path}?{query}"
        else:
            break
    
    return body
