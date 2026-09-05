def fetch_text(url: str, transport, resolve_host) -> str:
    # Validate protocol and port
    if not (url.startswith('http://') or url.startswith('https://')):
        raise ValueError("Only HTTP and HTTPS are allowed")
    
    # Extract hostname and port
    scheme = url.split('://')[0]
    path = url.split('://', 1)[1]
    
    # Determine default port
    default_port = 80 if scheme == 'http' else 443
    
    # Parse hostname and port
    if ':' in path:
        hostname, port_str = path.rsplit(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError("Invalid port number")
    else:
        hostname = path
        port = default_port
    
    # Resolve hostname to IP addresses
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError("No valid IP addresses found for hostname")
    
    # Construct full URL with resolved port
    if port == default_port:
        full_url = f"{scheme}://{hostname}{path}"
    else:
        full_url = f"{scheme}://{hostname}:{port}{path}"
    
    # Call transport to get response
    status, headers, body = transport(full_url)
    
    # Check status code
    if status != 200:
        raise ValueError("Only status 200 is allowed")
    
    # Return body as string
    return body.decode('utf-8') if isinstance(body, bytes) else body
