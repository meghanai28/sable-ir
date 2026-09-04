import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("disallowed scheme")
    
    if scheme == 'http':
        default_port = 80
    else:
        default_port = 443
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("disallowed port")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("missing hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("host resolution failed")
    
    if not ip_addresses:
        raise ValueError("non-public host")
    
    for ip in ip_addresses:
        ip = ip.strip()
        if ip == '':
            raise ValueError("non-public host")
        if ip.startswith('127.'):
            raise ValueError("non-public host")
        if ip.startswith('10.'):
            raise ValueError("non-public host")
        if ip.startswith('192.168.'):
            raise ValueError("non-public host")
        if ip.startswith('172.'):
            parts = ip.split('.')
            if len(parts) >= 2:
                try:
                    second_octet = int(parts[1])
                    if 16 <= second_octet <= 31:
                        raise ValueError("non-public host")
                except ValueError:
                    raise ValueError("non-public host")
        if ip == '0.0.0.0':
            raise ValueError("non-public host")
        if ip.startswith('169.254.'):
            raise ValueError("non-public host")
        if ip.startswith('::1') or ip == '::1':
            raise ValueError("non-public host")
        if ip.startswith('fc') or ip.startswith('fd'):
            raise ValueError("non-public host")
        if ip.startswith('fe80:'):
            raise ValueError("non-public host")
        if ip == '::' or ip == '0:0:0:0:0:0:0:0':
            raise ValueError("non-public host")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("redirect not allowed")
    
    if status != 200:
        raise ValueError("disallowed request")
    
    if isinstance(body, bytes):
        return body.decode('utf-8')
    return str(body)
