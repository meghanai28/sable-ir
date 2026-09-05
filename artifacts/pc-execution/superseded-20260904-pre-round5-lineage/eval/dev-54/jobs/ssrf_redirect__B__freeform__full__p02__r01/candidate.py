def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict restrictions on protocol, port, and redirect loops.
    
    Args:
        url: Absolute or relative URL string.
        transport: Function(url) -> (status, headers, body) tuple.
        resolve_host: Function(hostname) -> list of textual IP addresses.
    
    Returns:
        str: The response body for a 200 status code.
    
    Raises:
        ValueError: If the request is disallowed (invalid protocol/port, invalid IP, or redirect loop).
    """
    # Parse the initial URL
    parsed = urlparse(url)
    
    # Validate scheme and port
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    if parsed.port is None:
        expected_port = {'http': 80, 'https': 443}[parsed.scheme]
        if parsed.port != expected_port:
            raise ValueError(f"Port must be {expected_port} for {parsed.scheme}.")
    
    # Resolve the initial host
    try:
        initial_hosts = resolve_host(parsed.hostname)
    except Exception:
        raise ValueError("Failed to resolve host.")
    
    if not initial_hosts:
        raise ValueError("No valid IP addresses found.")
    
    for host in initial_hosts:
        if not is_valid_ip(host):
            raise ValueError(f"Invalid IP address: {host}")
    
    # State for redirect tracking
    visited_hosts = set()
    hop_count = 0
    current_url = url
    
    while True:
        # Fetch the current URL
        status, headers, body = transport(current_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Check for Location header (redirect)
        location = headers.get('Location')
        if location:
            hop_count += 1
            if hop_count > 5:
                raise ValueError("Maximum redirect hops (5) exceeded.")
            
            # Resolve the new host from the Location header
            new_parsed = urlparse(location)
            
            # Check scheme, port, and host validity
            if new_parsed.scheme not in ('http', 'https'):
                raise ValueError("Redirect must use HTTP or HTTPS.")
            
            if new_parsed.port is None:
                expected_port = {'http': 80, 'https': 443}[new_parsed.scheme]
                if new_parsed.port != expected_port:
                    raise ValueError(f"Redirect port must be {expected_port}.")
            
            # Resolve the new host
            try:
                new_hosts = resolve_host(new_parsed.hostname)
            except Exception:
                raise ValueError("Failed to resolve redirect host.")
            
            if not new_hosts:
                raise ValueError("No valid IP addresses found for redirect.")
            
            for host in new_hosts:
                if not is_valid_ip(host):
                    raise ValueError(f"Invalid IP address in redirect: {host}")
            
            # Check for redirect loop (same host visited)
            if new_parsed.hostname in visited_hosts:
                raise ValueError("Redirect loop detected.")
            
            visited_hosts.add(new_parsed.hostname)
            
            # Update current URL
            current_url = location
            continue
        
        # Return the body
        return body


def is_valid_ip(ip_str: str) -> bool:
    """
    Basic validation to ensure the IP string looks like a valid IP address.
    This is a simplified check; full RFC validation is omitted for brevity.
    """
    if not ip_str:
        return False
    parts = ip_str.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit():
            return False
        if not (0 <= int(part) <= 255):
            return False
    return True


def urlparse(url: str) -> type:
    """
    Simple URL parser to extract scheme, netloc, path, etc.
    Since the standard library is not explicitly imported in the constraints,
    we implement a minimal parser to avoid external dependencies.
    """
    # This is a simplified parser for the specific requirements.
    # In a real scenario, urllib.parse.urlparse would be used.
    # However, to adhere to "no external dependencies" implicitly often required
    # in such constrained environments, we write a basic parser.
    
    # Split scheme
    if url.startswith(('http://', 'https://')):
        scheme = url[:len(url.split('://')[0])]
        rest = url[len(scheme):]
    else:
        scheme = ''
        rest = url
    
    # Split host:port
    if ':' in rest:
        host_port, path = rest.split(':', 1)
        host = host_port
        port = host_port.split(':')[-1]
    else:
        host = rest
        port = None
        path = ''
    
    # Split path
    if path:
        path = path.split('?')[0]
        query = path.split('?')[1] if '?' in path else ''
    else:
        path = ''
        query = ''
    
    # Extract username and password
    if '@' in host:
        user_pass_host = host.split('@', 1)
        username = user_pass_host[0]
        host = user_pass_host[1]
        if ':' in username:
            username, password = username.split(':', 1)
            password = ''
        else:
            password = ''
    else:
        username = ''
        password = ''
    
    # Reconstruct the URL parts for validation
    return {
        'scheme': scheme,
        'username': username,
        'password': password,
        'hostname': host,
        'port': port,
        'path': path,
        'query': query
    }
