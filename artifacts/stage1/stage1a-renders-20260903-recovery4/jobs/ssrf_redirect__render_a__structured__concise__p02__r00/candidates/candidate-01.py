import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    host = parsed.hostname
    if host is None:
        raise ValueError("Missing host")
    
    if scheme == 'http':
        default_port = 80
    else:
        default_port = 443
    
    port = parsed.port
    if port is None:
        port = default_port
    
    if port != default_port:
        raise ValueError("Disallowed non-default port")
    
    try:
        ips = resolve_host(host)
    except Exception:
        raise ValueError("Host resolution failed")
    
    if not ips:
        raise ValueError("No IP addresses resolved")
    
    for ip in ips:
        ip_lower = ip.lower()
        if ip_lower.startswith('127.'):
            raise ValueError("Non-public destination")
        if ip_lower.startswith('10.'):
            raise ValueError("Non-public destination")
        if ip_lower.startswith('192.168.'):
            raise ValueError("Non-public destination")
        if ip_lower.startswith('172.'):
            parts = ip_lower.split('.')
            if len(parts) >= 2:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    raise ValueError("Non-public destination")
        if ip_lower.startswith('169.254.'):
            raise ValueError("Non-public destination")
        if ip_lower == '::1':
            raise ValueError("Non-public destination")
        if ip_lower == '0.0.0.0':
            raise ValueError("Non-public destination")
        if ip_lower.startswith('fc00:') or ip_lower.startswith('fd00:'):
            raise ValueError("Non-public destination")
        if ip_lower.startswith('fe80:'):
            raise ValueError("Non-public destination")
        if ip_lower.startswith('::ffff:127.'):
            raise ValueError("Non-public destination")
        if ip_lower.startswith('::ffff:10.'):
            raise ValueError("Non-public destination")
        if ip_lower.startswith('::ffff:192.168.'):
            raise ValueError("Non-public destination")
        if ip_lower.startswith('::ffff:172.'):
            parts = ip_lower.split('.')
            if len(parts) >= 2:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    raise ValueError("Non-public destination")
        if ip_lower.startswith('::ffff:169.254.'):
            raise ValueError("Non-public destination")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects not allowed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body
