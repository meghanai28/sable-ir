import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    host = parsed.hostname
    if host is None:
        raise ValueError("Missing host")
    
    if parsed.port is not None:
        port = parsed.port
    else:
        port = 443 if scheme == 'https' else 80
    
    if port != (443 if scheme == 'https' else 80):
        raise ValueError("Disallowed non-default port")
    
    host = host.lower()
    
    try:
        ips = resolve_host(host)
    except Exception:
        raise ValueError("Failed to resolve host")
    
    if not ips:
        raise ValueError("Non-public initial destination")
    
    for ip in ips:
        ip_lower = ip.lower()
        if ip_lower.startswith('127.'):
            raise ValueError("Non-public initial destination")
        if ip_lower.startswith('0.'):
            raise ValueError("Non-public initial destination")
        if ip_lower.startswith('10.'):
            raise ValueError("Non-public initial destination")
        if ip_lower.startswith('172.'):
            parts = ip_lower.split('.')
            if len(parts) >= 2:
                second = int(parts[1])
                if 16 <= second <= 31:
                    raise ValueError("Non-public initial destination")
        if ip_lower.startswith('192.168.'):
            raise ValueError("Non-public initial destination")
        if ip_lower == '169.254.0.0':
            raise ValueError("Non-public initial destination")
        if ip_lower.startswith('169.254.'):
            raise ValueError("Non-public initial destination")
        if ip_lower.startswith('fc') or ip_lower.startswith('fd'):
            raise ValueError("Non-public initial destination")
        if ip_lower == '::1':
            raise ValueError("Non-public initial destination")
        if ip_lower == '0.0.0.0':
            raise ValueError("Non-public initial destination")
        if ip_lower == '::':
            raise ValueError("Non-public initial destination")
        if ip_lower.startswith('fe80:'):
            raise ValueError("Non-public initial destination")
        if ip_lower.startswith('fec0:'):
            raise ValueError("Non-public initial destination")
        if ip_lower.startswith('ff'):
            raise ValueError("Non-public initial destination")
        if ip_lower.startswith('::ffff:127.'):
            raise ValueError("Non-public initial destination")
        if ip_lower.startswith('::ffff:0.'):
            raise ValueError("Non-public initial destination")
        if ip_lower.startswith('::ffff:10.'):
            raise ValueError("Non-public initial destination")
        if ip_lower.startswith('::ffff:172.'):
            rest = ip_lower[len('::ffff:172.'):]
            parts = rest.split('.')
            if len(parts) >= 1:
                second = int(parts[0])
                if 16 <= second <= 31:
                    raise ValueError("Non-public initial destination")
        if ip_lower.startswith('::ffff:192.168.'):
            raise ValueError("Non-public initial destination")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect rejected")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    if isinstance(body, bytes):
        return body.decode('utf-8')
    
    return str(body)
