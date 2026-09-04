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
        raise ValueError("Failed to resolve host")
    
    if not ips:
        raise ValueError("No IP addresses resolved")
    
    for ip in ips:
        if ip.startswith('127.') or ip == '::1' or ip.startswith('0.') or ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('169.254.'):
            raise ValueError("Non-public destination")
        if ip.startswith('172.'):
            parts = ip.split('.')
            if len(parts) >= 2:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    raise ValueError("Non-public destination")
        if ':' in ip:
            lower_ip = ip.lower()
            if lower_ip.startswith('fc') or lower_ip.startswith('fd') or lower_ip == '::1' or lower_ip.startswith('fe80:'):
                raise ValueError("Non-public destination")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body
