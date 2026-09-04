import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if not parsed.hostname:
        raise ValueError("URL must have a hostname")
    
    default_port = 443 if parsed.scheme == 'https' else 80
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Only default ports are allowed")
    
    ip_addresses = resolve_host(parsed.hostname)
    
    for ip in ip_addresses:
        if ip.startswith('127.') or ip == '0.0.0.0' or ip == '::1' or ip.startswith('::ffff:127.'):
            raise ValueError("Localhost addresses are not allowed")
        if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
            if ip.startswith('172.'):
                second_octet = int(ip.split('.')[1])
                if 16 <= second_octet <= 31:
                    raise ValueError("Private addresses are not allowed")
            else:
                raise ValueError("Private addresses are not allowed")
        if ip.startswith('169.254.'):
            raise ValueError("Link-local addresses are not allowed")
        if ip.startswith('fc00:') or ip.startswith('fd00:'):
            raise ValueError("Private addresses are not allowed")
        if ip == '::' or ip == '0:0:0:0:0:0:0:0':
            raise ValueError("Unspecified addresses are not allowed")
    
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
