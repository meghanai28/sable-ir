def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict validation to prevent open redirects and
    traversal attacks. Only HTTP/HTTPS on default ports are allowed.
    """
    from urllib.parse import urlparse, urljoin, unquote
    from urllib.error import URLError
    import socket

    # Parse the initial URL
    parsed = urlparse(url)
    
    # Validate scheme and port
    valid_schemes = {'http', 'https'}
    if parsed.scheme.lower() not in valid_schemes:
        raise ValueError(f"Disallowed scheme: {parsed.scheme}")
    
    default_port = {'http': 80, 'https': 443}.get(parsed.scheme.lower())
    if parsed.port is None:
        parsed = parsed._replace(port=default_port)
    elif parsed.port != default_port:
        raise ValueError(f"Only HTTP/HTTPS on default port {default_port} allowed")

    # Resolve hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {e}")

    # Normalize path to prevent traversal
    path = parsed.path
    if path.startswith('..') or '..' in path:
        raise ValueError("Path traversal detected")
    
    # Ensure path is absolute and clean
    if not path.startswith('/'):
        path = '/' + path
    # Remove multiple slashes and trailing slashes (except root)
    while path.startswith('//'):
        path = path[1:]
    if path.endswith('/') and path != '/':
        path = path.rstrip('/')

    # Build the initial effective URL
    effective_url = f"{parsed.scheme}://{hostname}{path}"
    if parsed.query:
        effective_url += f"?{parsed.query}"

    # Validate initial destination against a safe base (using the resolved hostname scheme)
    # We treat the resolved scheme + hostname as the "public URL" root
    safe_base = f"{parsed.scheme}://{hostname}"
    if not effective_url.startswith(safe_base):
        raise ValueError("Effective URL does not start with the requested public URL")

    # Capture initial Location header
    status, headers, body = transport(url)
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    location = None
    if 'location' in headers:
        location = headers['location']
        # If it's absolute, it's a redirect; we reject it per plan
        if location.startswith(('http://', 'https://')):
            raise ValueError("Redirect detected: open redirect risk")

    # If no Location, we proceed with the initial URL
    current_url = url
    while True:
        # Check for traversal in current URL path/query
        parsed_current = urlparse(current_url)
        if parsed_current.path.startswith('..') or '..' in parsed_current.path:
            raise ValueError("Path traversal detected in redirect")
        
        # Validate scheme/port again for safety
        if parsed_current.scheme.lower() not in valid_schemes:
            raise ValueError(f"Disallowed scheme in redirect: {parsed_current.scheme}")
        
        default_port = {'http': 80, 'https': 443}.get(parsed_current.scheme.lower())
        if parsed_current.port is None:
            parsed_current = parsed_current._replace(port=default_port)
        elif parsed_current.port != default_port:
            raise ValueError(f"Only HTTP/HTTPS on default port {default_port} allowed")

        # Resolve hostname
        hostname_current = parsed_current.hostname
        if not hostname_current:
            raise ValueError("Invalid URL in redirect: missing hostname")
        
        try:
            ip_addresses = resolve_host(hostname_current)
        except Exception as e:
            raise ValueError(f"Failed to resolve hostname: {e}")

        # Build effective URL for this step
        path = parsed_current.path
        if path.startswith('..') or '..' in path:
            raise ValueError("Path traversal detected")
        if not path.startswith('/'):
            path = '/' + path
        while path.startswith('//'):
            path = path[1:]
        if path.endswith('/') and path != '/':
            path = path.rstrip('/')
        
        effective_url = f"{parsed_current.scheme}://{hostname_current}{path}"
        if parsed_current.query:
            effective_url += f"?{parsed_current.query}"

        # Safety check: ensure we haven't escaped the base
        safe_base = f"{parsed_current.scheme}://{hostname_current}"
        if not effective_url.startswith(safe_base):
            raise ValueError("Effective URL escaped the requested public URL")

        # Check for Location header in this response
        status, headers, body = transport(current_url)
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        if 'location' in headers:
            location = headers['location']
            if location.startswith(('http://', 'https://')):
                raise ValueError("Redirect detected: open redirect risk")
            # Update current_url for next iteration
            current_url = location
            continue
        else:
            break

    # Final validation of the destination before reading body
    parsed_final = urlparse(current_url)
    if not parsed_final.path.startswith('/'):
        parsed_final = parsed_final._replace(path='/' + parsed_final.path)
    while parsed_final.path.startswith('//'):
        parsed_final = parsed_final._replace(path=parsed_final.path[1:])
    if parsed_final.path.endswith('/') and parsed_final.path != '/':
        parsed_final = parsed_final._replace(path=parsed_final.path.rstrip('/'))
    
    final_effective = f"{parsed_final.scheme}://{parsed_final.hostname}{parsed_final.path}"
    if parsed_final.query:
        final_effective += f"?{parsed_final.query}"
    
    safe_base_final = f"{parsed_final.scheme}://{parsed_final.hostname}"
    if not final_effective.startswith(safe_base_final):
        raise ValueError("Final destination escaped the requested public URL")

    # Read and return body
    if not body:
        raise ValueError("Empty response body")
    
    return body
