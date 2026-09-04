import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    host = parsed.hostname
    if host is None:
        raise ValueError("URL must have a host")
    
    if scheme == 'http':
        default_port = 80
    else:
        default_port = 443
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Only default port allowed")
    
    if parsed.port is None:
        port = default_port
    else:
        port = parsed.port
    
    try:
        ips = resolve_host(host)
    except Exception:
        raise ValueError("Failed to resolve host")
    
    if not ips:
        raise ValueError("Host resolved to no IP addresses")
    
    for ip in ips:
        if ip.startswith('127.') or ip.startswith('10.') or ip.startswith('192.168.'):
            raise ValueError("Private IP addresses not allowed")
        if ip.startswith('172.'):
            parts = ip.split('.')
            if len(parts) >= 2:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    raise ValueError("Private IP addresses not allowed")
        if ip.startswith('169.254.'):
            raise ValueError("Link-local addresses not allowed")
        if ip == '::1':
            raise ValueError("Private IP addresses not allowed")
        if ip.startswith('fc00:') or ip.startswith('fd00:'):
            raise ValueError("Private IP addresses not allowed")
        if ip.startswith('fe80:'):
            raise ValueError("Link-local addresses not allowed")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects are not allowed")
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
