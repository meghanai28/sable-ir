def fetch_text(url: str, transport, resolve_host) -> str:
    if url.startswith(('http://', 'https://')):
        raise ValueError("Absolute URLs are not allowed")
    
    hostname = url.split('/')[0]
    resolved_ips = resolve_host(hostname)
    
    if not resolved_ips:
        raise ValueError("Hostname resolution failed")
    
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError("Unexpected status code")
    
    return body.decode('utf-8') if isinstance(body, bytes) else body
