import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    default_port = 443 if parsed.scheme == 'https' else 80
    host = parsed.hostname
    port = parsed.port
    
    if port is not None and port != default_port:
        raise ValueError("Disallowed non-default port")
    
    if host is None:
        raise ValueError("Missing host")
    
    resolved_ips = resolve_host(host)
    if not resolved_ips:
        raise ValueError("Non-public destination")
    
    for ip in resolved_ips:
        if ip.startswith('127.') or ip.startswith('10.') or ip.startswith('192.168.'):
            raise ValueError("Non-public destination")
        if ip.startswith('172.'):
            octets = ip.split('.')
            if len(octets) >= 2:
                second = int(octets[1])
                if 16 <= second <= 31:
                    raise ValueError("Non-public destination")
        if ip.startswith('169.254.'):
            raise ValueError("Non-public destination")
        if ip == '0.0.0.0':
            raise ValueError("Non-public destination")
        if ':' in ip:
            if ip == '::1' or ip == '::' or ip.startswith('fc') or ip.startswith('fd') or ip.startswith('fe80:'):
                raise ValueError("Non-public destination")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Disallowed status")
    
    return body
