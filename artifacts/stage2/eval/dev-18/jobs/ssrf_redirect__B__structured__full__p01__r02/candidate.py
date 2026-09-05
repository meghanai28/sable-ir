def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with security validations.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns textual IP addresses.
    
    Returns:
        str: The body of the HTTP response for status 200.
    
    Raises:
        ValueError: If the scheme is not http/https, port is not default, hostname cannot be resolved,
                   or if redirects violate security constraints.
    """
    # Parse initial URL
    from urllib.parse import urlparse, urljoin
    
    initial_url = url
    parsed = urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Validate port
    default_port = {'http': 80, 'https': 443}[parsed.scheme]
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Only default ports are allowed")
    
    # Resolve and check hostname
    hostname = parsed.netloc
    if not hostname:
        raise ValueError("Invalid URL")
    
    # Remove port from hostname for resolution if present
    if parsed.port is not None:
        hostname = hostname.split(':')[0]
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Hostname cannot be resolved")
    
    if not ip_addresses:
        raise ValueError("No IP addresses found")
    
    # Current URL for redirect handling
    current_url = initial_url
    
    # Follow redirects (max 5)
    redirect_count = 0
    
    while True:
        # Resolve current URL hostname
        current_parsed = urlparse(current_url)
        current_hostname = current_parsed.netloc
        if current_parsed.port is not None:
            current_hostname = current_hostname.split(':')[0]
        
        try:
            resolved_ips = resolve_host(current_hostname)
        except Exception:
            raise ValueError("Hostname cannot be resolved")
        
        if not resolved_ips:
            raise ValueError("No IP addresses found")
        
        # Get response
        status, headers, body = transport(current_url)
        
        # Check status
        if status != 200:
            raise ValueError("Expected status 200")
        
        # Check for redirects
        location = headers.get('Location')
        if location:
            redirect_count += 1
            if redirect_count > 5:
                raise ValueError("Too many redirects")
            
            # Resolve Location against current URL
            new_url = urljoin(current_url, location)
            new_parsed = urlparse(new_url)
            
            # Check scheme
            if new_parsed.scheme not in ('http', 'https'):
                raise ValueError("Redirect to disallowed scheme")
            
            # Check port
            new_default_port = {'http': 80, 'https': 443}[new_parsed.scheme]
            if new_parsed.port is not None and new_parsed.port != new_default_port:
                raise ValueError("Redirect to non-default port")
            
            # Check for .. segments
            if '..' in new_parsed.path:
                raise ValueError("Path contains .. segments")
            
            # Check same scheme and port as initial request
            if new_parsed.scheme != parsed.scheme or new_parsed.port != parsed.port:
                raise ValueError("Redirect must preserve scheme and port")
            
            current_url = new_url
            continue
        
        return body
