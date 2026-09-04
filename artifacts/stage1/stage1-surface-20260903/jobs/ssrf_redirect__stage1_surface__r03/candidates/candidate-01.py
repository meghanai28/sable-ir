import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if parsed.hostname is None:
        raise ValueError("URL must have a hostname")
    
    default_port = 443 if parsed.scheme == 'https' else 80
    port = parsed.port if parsed.port is not None else default_port
    
    if port != default_port:
        raise ValueError("Only default ports are allowed")
    
    if '@' in parsed.netloc:
        raise ValueError("Userinfo in URL is not allowed")
    
    ip_addresses = resolve_host(parsed.hostname)
    
    for ip in ip_addresses:
        if ip.startswith('127.') or ip == '0.0.0.0' or ip == '::1' or ip == '::':
            raise ValueError("Loopback or unspecified addresses are not allowed")
        
        if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
            parts = ip.split('.')
            if ip.startswith('10.'):
                raise ValueError("Private addresses are not allowed")
            if ip.startswith('192.168.'):
                raise ValueError("Private addresses are not allowed")
            if ip.startswith('172.') and len(parts) > 1:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    raise ValueError("Private addresses are not allowed")
        
        if ':' in ip:
            if ip.startswith('fc') or ip.startswith('fd'):
                raise ValueError("Private addresses are not allowed")
            if ip == 'fe80::1' or ip.startswith('fe80:'):
                raise ValueError("Link-local addresses are not allowed")
    
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body.decode('utf-8') if isinstance(body, bytes) else body
