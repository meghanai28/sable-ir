import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    default_port = 443 if parsed.scheme == 'https' else 80
    port = parsed.port
    if port is None:
        port = default_port
    if port != default_port:
        raise ValueError("Disallowed port")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    try:
        ips = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve host")
    
    if not ips:
        raise ValueError("No IP addresses resolved")
    
    for ip in ips:
        ip_lower = ip.lower().strip()
        if ip_lower.startswith('127.') or ip_lower == '::1' or ip_lower == '0:0:0:0:0:0:0:1':
            raise ValueError("Non-public destination")
        if ip_lower.startswith('10.') or ip_lower.startswith('192.168.') or ip_lower.startswith('172.'):
            second_octet = int(ip_lower.split('.')[1]) if len(ip_lower.split('.')) > 1 else 0
            if ip_lower.startswith('172.') and 16 <= second_octet <= 31:
                raise ValueError("Non-public destination")
            elif not ip_lower.startswith('172.'):
                raise ValueError("Non-public destination")
        if ip_lower == '0.0.0.0':
            raise ValueError("Non-public destination")
        if ip_lower.startswith('fc') or ip_lower.startswith('fd'):
            raise ValueError("Non-public destination")
        if ip_lower.startswith('fe80:'):
            raise ValueError("Non-public destination")
        if ip_lower.startswith('169.254.'):
            raise ValueError("Non-public destination")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Disallowed status")
    
    return body
