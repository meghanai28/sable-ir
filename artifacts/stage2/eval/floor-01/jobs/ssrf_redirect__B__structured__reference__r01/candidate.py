def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation and redirect handling.
    
    Args:
        url: The initial URL to fetch.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of textual IP addresses.
    
    Returns:
        The response body for a 200 status code.
    
    Raises:
        ValueError: If validation fails, no valid addresses are found, or too many redirects.
    """
    current_url = url
    redirect_count = 0
    max_redirects = 5
    
    while True:
        # Validation of current_url
        if not current_url:
            raise ValueError("URL cannot be empty")
        
        # Parse scheme and host
        if not current_url.startswith(('http://', 'https://')):
            raise ValueError("Disallowed scheme")
        
        scheme = current_url[:4]
        rest = current_url[4:]
        
        # Check for credentials
        if '@' in rest:
            raise ValueError("Username or password not allowed")
        
        # Determine port and host
        if rest.startswith('://'):
            rest = rest[3:]
        
        # Split host and path
        if '/' in rest:
            host_part, path = rest.split('/', 1)
        else:
            host_part = rest
            path = ''
        
        # Extract port
        if ':' in host_part:
            host, port_str = host_part.rsplit(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                raise ValueError("Invalid port number")
        else:
            host = host_part
            port = None
        
        # Validate scheme and port
        if scheme == 'http':
            if port is not None and port != 80:
                raise ValueError("Invalid port for HTTP")
        elif scheme == 'https':
            if port is not None and port != 443:
                raise ValueError("Invalid port for HTTPS")
        else:
            raise ValueError("Disallowed scheme")
        
        # Resolve hostname
        addresses = resolve_host(host)
        if not addresses:
            raise ValueError("No valid addresses found")
        
        # Check if any address is not a global public address
        # Assuming all resolved IPs are public unless specified otherwise
        # In a real scenario, one might check against a blocklist
        for addr in addresses:
            # Simple check: if it's a private IP range, raise error
            # 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, etc.
            parts = addr.split('.')
            if len(parts) == 4:
                try:
                    first = int(parts[0])
                    second = int(parts[1])
                    if (first == 10) or (first == 172 and 16 <= second <= 31) or (first == 192 and second == 168):
                        raise ValueError("Non-public address found")
                except ValueError:
                    raise ValueError("Invalid IP address format")
        
        # Make request
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        # Handle redirect
        if 'location' in headers.lower():
            location = headers['location']
            redirect_count += 1
            
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
            
            # Resolve redirect location
            if not location.startswith(('http://', 'https://')):
                # Relative URL
                base = current_url
                if base.endswith('/'):
                    base = base[:-1]
                if base.endswith('?'):
                    base = base[:-1]
                    path = base[base.rfind('/'):]
                    if not path:
                        path = '/'
                    else:
                        path = path
                else:
                    path = current_url[current_url.rfind('/'):]
                    if not path:
                        path = '/'
                    else:
                        path = path
                
                if not location.startswith('/'):
                    location = base + '/' + location
                else:
                    location = base + location
                
                if '?' in location:
                    location = location.split('?', 1)[0]
                if '#' in location:
                    location = location.split('#', 1)[0]
                
                if not location.startswith(('http://', 'https://')):
                    raise ValueError("Invalid redirect URL")
            else:
                if not location.startswith(('http://', 'https://')):
                    raise ValueError("Invalid redirect URL")
            
            current_url = location
        else:
            break
    
    raise ValueError("No 200 status reached")
