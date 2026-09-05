def fetch_text(url: str, transport, resolve_host) -> str:
    if url.startswith('http://'):
        scheme = 'http'
    elif url.startswith('https://'):
        scheme = 'https'
    else:
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    hostname = url.split('://')[1]
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("No IP addresses resolved for hostname")
    
    port = None
    if scheme == 'http':
        port = 80
    elif scheme == 'https':
        port = 443
    
    status, headers, body = transport(url)
    if status != 200:
        raise ValueError("Only status 200 is allowed")
    
    return body.decode('utf-8') if isinstance(body, bytes) else body
