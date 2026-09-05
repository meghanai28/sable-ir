def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL following a safety plan for HTTP/HTTPS requests.
    
    Args:
        url: The URL to fetch (absolute or relative).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns textual IP addresses.
    
    Returns:
        The body of the response for status code 200.
    
    Raises:
        ValueError: If the scheme is not HTTP/HTTPS, or if the request violates safety rules.
    """
    # Parse the initial URL
    parsed_url = urlparse(url)
    
    # Validate scheme
    if parsed_url.scheme not in ['http', 'https']:
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Validate port
    default_port = {'http': 80, 'https': 443}
    if parsed_url.port is None:
        port = default_port[parsed_url.scheme]
    else:
        port = parsed_url.port
    
    if port != default_port[parsed_url.scheme]:
        raise ValueError("Only default ports are allowed")
    
    # Resolve the initial hostname
    initial_host = parsed_url.hostname
    if initial_host is None:
        raise ValueError("Invalid URL")
    
    resolved_ips = resolve_host(initial_host)
    if not resolved_ips:
        raise ValueError("DNS resolution failed")
    
    # Build the initial URL object for tracking
    current_url = parsed_url
    
    # Follow Location headers (max 5 hops)
    hop_count = 0
    while hop_count < 5:
        # Transport the current URL
        status, headers, body = transport(current_url.geturl())
        
        # Check status code
        if status != 200:
            raise ValueError("Unexpected status code")
        
        # Extract Location header
        location = headers.get('Location')
        if location:
            # Parse the Location header
            loc_parsed = urlparse(location)
            
            # Validate scheme
            if loc_parsed.scheme not in ['http', 'https']:
                raise ValueError("Location header has invalid scheme")
            
            # Validate port
            if loc_parsed.port is None:
                loc_port = default_port[loc_parsed.scheme]
            else:
                loc_port = loc_parsed.port
            
            if loc_port != default_port[loc_parsed.scheme]:
                raise ValueError("Location header has non-default port")
            
            # Check credentials match
            if parsed_url.username or parsed_url.password:
                if not (loc_parsed.username and loc_parsed.password):
                    raise ValueError("Credentials mismatch in Location header")
            
            # Resolve DNS for the Location
            loc_host = loc_parsed.hostname
            if loc_host is None:
                raise ValueError("Invalid hostname in Location header")
            
            loc_resolved = resolve_host(loc_host)
            if not loc_resolved:
                raise ValueError("DNS resolution failed for Location")
            
            # Check that the resolved IPs are valid (basic check)
            for ip in loc_resolved:
                if not is_valid_ip(ip):
                    raise ValueError("Invalid IP address in Location header")
            
            # Update current URL for the next hop
            current_url = loc_parsed
            hop_count += 1
        else:
            # No Location header, we're done
            break
    
    # Final validation of the destination
    final_scheme = current_url.scheme
    final_port = current_url.port if current_url.port else default_port[final_scheme]
    
    if final_scheme not in ['http', 'https']:
        raise ValueError("Final destination has invalid scheme")
    
    if final_port != default_port[final_scheme]:
        raise ValueError("Final destination has non-default port")
    
    final_host = current_url.hostname
    if final_host is None:
        raise ValueError("Invalid hostname in final destination")
    
    final_resolved = resolve_host(final_host)
    if not final_resolved:
        raise ValueError("DNS resolution failed for final destination")
    
    for ip in final_resolved:
        if not is_valid_ip(ip):
            raise ValueError("Invalid IP address in final destination")
    
    # Return the body
    return body

def is_valid_ip(ip):
    """
    Basic validation of IP address format.
    """
    import re
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    parts = ip.split('.')
    for part in parts:
        if not (0 <= int(part) <= 255):
            return False
    return True

def urlparse(url):
    """
    Simple URL parser to avoid external dependencies.
    """
    import re
    
    # Match basic URL pattern
    match = re.match(r'^([a-zA-Z][a-zA-Z0-9+.-]*):\/\/([^\/?#]*)(?:\?([^#]*))?(?:#(.*))?', url)
    if not match:
        return None
    
    scheme = match.group(1)
    netloc = match.group(2)
    query = match.group(3)
    fragment = match.group(4)
    
    # Parse netloc for host, port, username, password
    netloc_match = re.match(r'^([^:]+):(\d+)(?:@(.+))?$', netloc)
    if netloc_match:
        host = netloc_match.group(1)
        port = int(netloc_match.group(2))
        username = None
        password = None
        if netloc_match.group(3):
            username = netloc_match.group(3).split(':')[0]
            password = netloc_match.group(3).split(':')[-1] if ':' in netloc_match.group(3) else ''
    else:
        host = netloc
        port = None
        username = None
        password = None
    
    # Handle relative URLs
    if not scheme:
        return None
    
    return {
        'scheme': scheme,
        'netloc': netloc,
        'hostname': host,
        'port': port,
        'username': username,
        'password': password,
        'path': '',
        'query': query,
        'fragment': fragment
    }

def is_valid_ip(ip):
    """
    Basic validation of IP address format.
    """
    import re
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    parts = ip.split('.')
    for part in parts:
        if not (0 <= int(part) <= 255):
            return False
    return True

def urlparse(url):
    """
    Simple URL parser to avoid external dependencies.
    """
    import re
    
    # Match basic URL pattern
    match = re.match(r'^([a-zA-Z][a-zA-Z0-9+.-]*):\/\/([^\/?#]*)(?:\?([^#]*))?(?:#(.*))?', url)
    if not match:
        return None
    
    scheme = match.group(1)
    netloc = match.group(2)
    query = match.group(3)
    fragment = match.group(4)
    
    # Parse netloc for host, port, username, password
    netloc_match = re.match(r'^([^:]+):(\d+)(?:@(.+))?$', netloc)
    if netloc_match:
        host = netloc_match.group(1)
        port = int(netloc_match.group(2))
        username = None
        password = None
        if netloc_match.group(3):
            username = netloc_match.group(3).split(':')[0]
            password = netloc_match.group(3).split(':')[-1] if ':' in netloc_match.group(3) else ''
    else:
        host = netloc
        port = None
        username = None
        password = None
    
    # Handle relative URLs
    if not scheme:
        return None
    
    return {
        'scheme': scheme,
        'netloc': netloc,
        'hostname': host,
        'port': port,
        'username': username,
        'password': password,
        'path': '',
        'query': query,
        'fragment': fragment
    }
