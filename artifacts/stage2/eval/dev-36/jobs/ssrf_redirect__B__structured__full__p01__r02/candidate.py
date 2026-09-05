def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL using the provided transport and DNS resolver.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The response body for a 200 status code.
    
    Raises:
        ValueError: If the scheme is not http or https, or if no IP address is found for the hostname.
    """
    # Parse the URL to extract scheme, host, port, and path
    from urllib.parse import urlparse, urljoin, parse_qs
    
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme.lower()
    
    # GUARD: Check scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Determine the default port based on scheme
    default_port = {'http': 80, 'https': 443}[scheme]
    
    # Extract host and port
    host = parsed_url.hostname
    port = parsed_url.port
    path = parsed_url.path
    
    # GUARD: Resolve host
    if not host:
        raise ValueError("Invalid URL: missing hostname.")
    
    ip_addresses = resolve_host(host)
    if not ip_addresses:
        raise ValueError(f"No IP address found for hostname: {host}")
    
    # Construct the initial request URL
    if port:
        request_url = f"{scheme}://{host}:{port}{path}"
    else:
        request_url = f"{scheme}://{host}{path}"
    
    # Follow redirects
    current_url = request_url
    max_redirects = 5
    redirect_count = 0
    
    while True:
        # Call transport
        status, headers, body = transport(current_url)
        
        # GUARD: Check status code
        if status != 200:
            # If it's a redirect, follow it; otherwise, raise error
            if 'location' in headers:
                location = headers['location']
                current_url = location
                redirect_count += 1
                if redirect_count > max_redirects:
                    raise ValueError("Too many redirects.")
                continue
            else:
                raise ValueError(f"Request failed with status code: {status}")
        
        # GUARD: Check for redirect in headers
        if 'location' in headers:
            location = headers['location']
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects.")
            
            # Resolve the new URL
            new_parsed = urlparse(location)
            new_scheme = new_parsed.scheme.lower()
            
            # GUARD: Check scheme consistency
            if new_scheme != scheme:
                raise ValueError("Redirect to different scheme not allowed.")
            
            # Check port consistency
            if port:
                new_port = new_parsed.port
                if new_port != port:
                    raise ValueError("Redirect to different port not allowed.")
            else:
                new_port = new_parsed.port
                if new_port is not None:
                    raise ValueError("Redirect to port not allowed when current has no port.")
            
            # Check for missing credentials
            if new_parsed.username or new_parsed.password:
                raise ValueError("Redirect with credentials not allowed.")
            
            # Check DNS entry (assuming resolve_host handles this)
            new_host = new_parsed.hostname
            if not new_host:
                raise ValueError("Invalid hostname in redirect.")
            
            new_ip_addresses = resolve_host(new_host)
            if not new_ip_addresses:
                raise ValueError(f"No IP address found for hostname in redirect: {new_host}")
            
            # Construct the new URL
            if new_port:
                current_url = f"{new_scheme}://{new_host}:{new_port}{new_parsed.path}"
            else:
                current_url = f"{new_scheme}://{new_host}{new_parsed.path}"
            
            continue
        
        # Return the body for status 200
        return body
