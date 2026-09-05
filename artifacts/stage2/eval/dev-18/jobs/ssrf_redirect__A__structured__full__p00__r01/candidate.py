def fetch_text(url: str, transport, resolve_host) -> str:
    scheme, _, rest = url.partition('://')
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if not scheme.startswith(('http', 'https')):
        raise ValueError("Invalid scheme")
    
    host = rest.split('/')[0]
    if '..' in host:
        raise ValueError("Path traversal detected in host")
    
    resolved_ips = resolve_host(host)
    if not resolved_ips or len(resolved_ips) > 1:
        raise ValueError("Invalid or multiple IP addresses")
    
    port = None
    if scheme == 'http':
        port = 80
    elif scheme == 'https':
        port = 443
    
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError("Non-200 status code")
    
    return body.decode('utf-8') if isinstance(body, bytes) else body
