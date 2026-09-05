def fetch_text(url: str, transport, resolve_host) -> str:
    # Validate scheme
    if not (url.startswith('http://') or url.startswith('https://')):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Extract scheme, host, and port
    scheme = url.split('://')[0]
    if scheme == 'http':
        port = 80
    else:
        port = 443
    
    # Parse the rest of the URL to get host and path
    rest = url[len(url.split('://')[0]) + 3:]
    if ':' in rest:
        host, path = rest.rsplit(':', 1)
        if not path:
            path = '/'
    else:
        host, path = rest, '/'
    
    # Resolve hostname
    resolved_ips = resolve_host(host)
    if not resolved_ips:
        raise ValueError("Failed to resolve hostname")
    
    # Use the first IP address for connection
    ip_address = resolved_ips[0]
    
    # Construct the full URL with resolved IP
    full_url = f"{scheme}://{ip_address}{path}"
    
    # Make the request
    status, headers, body = transport(full_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Request failed with status {status}")
    
    return body
