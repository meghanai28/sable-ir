import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    default_port = 443 if parsed.scheme == 'https' else 80
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Disallowed non-default port")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Host resolution failed")
    
    if not ip_addresses:
        raise ValueError("Host resolution returned no addresses")
    
    for ip in ip_addresses:
        if ip.startswith('127.') or ip.startswith('0.') or ip == '::1' or ip.startswith('::ffff:127.') or ip.startswith('::ffff:0.'):
            raise ValueError("Disallowed private destination")
        if ip.startswith('10.') or ip.startswith('172.') or ip.startswith('192.168.'):
            raise ValueError("Disallowed private destination")
        if ip.startswith('fc') or ip.startswith('fd'):
            raise ValueError("Disallowed private destination")
        if ip == '0.0.0.0' or ip == '::':
            raise ValueError("Disallowed private destination")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects not followed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    if isinstance(body, bytes):
        body = body.decode('utf-8', errors='replace')
    
    return body
