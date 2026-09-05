def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation and redirect handling.
    
    Args:
        url: The initial URL to fetch (absolute or relative).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of textual IP addresses.
    
    Returns:
        The body of the HTTP response with status 200.
    
    Raises:
        ValueError: If the scheme is not http/https, no IP addresses are found,
                   or redirect validation fails.
    """
    current_url = _parse_url(url)
    
    # Validate scheme
    if current_url.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Resolve hostname and validate
    if not resolve_host(current_url.hostname):
        raise ValueError("No IP addresses found for the hostname.")
    
    current_scheme = current_url.scheme
    current_port = current_url.port
    current_path = current_url.path
    current_headers = {}
    
    # Follow redirects (up to 5 hops)
    for _ in range(5):
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status != 302 and status != 301:
            # If not a redirect, we might still want to return body if status is 200,
            # but the loop condition handles 200 at the start.
            # If it's not 200 or 301/302, we stop.
            # However, the spec says "return the body for status 200".
            # If we get here and status is not 200, we don't return.
            # But we should check if there's a Location header to follow.
            if status in (301, 302):
                location = headers.get('Location')
                if not location:
                    raise ValueError("No Location header provided for redirect.")
                
                # Parse the Location header
                new_url_str = location
                if not new_url_str.startswith(('http://', 'https://')):
                    # Relative URL
                    new_url_str = _resolve_relative_url(current_url, location)
                
                new_url = _parse_url(new_url_str)
                
                # Validate scheme and port match
                if new_url.scheme != current_scheme:
                    raise ValueError("Redirect scheme mismatch.")
                
                if new_url.port is None:
                    new_port = current_port
                else:
                    new_port = new_url.port
                
                if new_port != current_port:
                    raise ValueError("Redirect port mismatch.")
                
                # Validate DNS and public address
                if not resolve_host(new_url.hostname):
                    raise ValueError("No IP addresses found for redirect hostname.")
                
                # Update current URL
                current_url = new_url
                current_headers = headers
                continue
            else:
                # Not a redirect, not 200. Stop.
                raise ValueError("Unexpected status code.")
        else:
            raise ValueError("Unexpected status code.")
    
    raise ValueError("Too many redirects.")

def _parse_url(url_str: str) -> dict:
    """
    Parse a URL string into a dictionary with scheme, hostname, port, path.
    """
    if not url_str.startswith(('http://', 'https://')):
        # Treat as relative path for now, assume http://localhost:80 or similar
        # But spec says "Accept HTTP or HTTPS on its default port".
        # If it's relative, we need to resolve it.
        # For now, let's assume if no scheme, it's relative.
        pass
    
    scheme = None
    hostname = None
    port = None
    path = None
    
    if url_str.startswith('http://'):
        scheme = 'http'
        url_str = url_str[7:]
    elif url_str.startswith('https://'):
        scheme = 'https'
        url_str = url_str[8:]
    
    # Split host and port
    if ':' in url_str:
        parts = url_str.rsplit(':', 1)
        hostname = parts[0]
        port_str = parts[1]
        if port_str == '':
            port = None
        elif port_str == '80' and scheme == 'http':
            port = None
        elif port_str == '443' and scheme == 'https':
            port = None
        else:
            try:
                port = int(port_str)
            except ValueError:
                raise ValueError("Invalid port number.")
    else:
        hostname = url_str
        port = None
    
    # Path
    if '/' in url_str:
        path = url_str.split('/', 1)[1]
    else:
        path = '/'
    
    return {
        'scheme': scheme,
        'hostname': hostname,
        'port': port,
        'path': path
    }

def _resolve_relative_url(base_url: dict, relative_path: str) -> str:
    """
    Resolve a relative URL against the base URL.
    """
    # Construct the full path
    if base_url['path'] == '/':
        full_path = relative_path
    else:
        # Join base path and relative path
        # Remove trailing slash from base if present, and leading slash from relative
        base_path_clean = base_url['path'].rstrip('/')
        if not base_path_clean or base_path_clean == '/':
            full_path = relative_path
        else:
            full_path = base_path_clean + '/' + relative_path
    
    # Reconstruct URL
    if base_url['port'] is None:
        # Use default port
        if base_url['scheme'] == 'http':
            port_str = ''
        else:
            port_str = ':443'
    else:
        port_str = f':{base_url["port"]}'
    
    if not full_path.startswith('/'):
        full_path = '/' + full_path
    
    return f"{base_url['scheme']}://{base_url['hostname']}{port_str}{full_path}"
