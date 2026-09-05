def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    # Validate scheme
    if not (url.startswith('http://') or url.startswith('https://')):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Extract hostname
    if '://' in url:
        url = url.split('://', 1)[1]
    if '?' in url:
        url = url.split('?', 1)[0]
    
    hostname = url.split('/')[0]
    
    # Resolve hostname
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError("No valid IP addresses resolved for hostname")
    
    # Determine port and protocol
    if url.startswith('https://'):
        scheme = 'https'
        port = 443
    else:
        scheme = 'http'
        port = 80
    
    # Build URL with port if needed
    if ':' in hostname:
        final_url = f"{url.split('://', 1)[1]}:{port}"
    else:
        final_url = f"{url.split('://', 1)[1]}:{port}"
    
    # Make request
    status, headers, body = transport(final_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
