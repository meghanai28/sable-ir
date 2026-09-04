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
        raise ValueError("Failed to resolve host")
    
    if not ip_addresses:
        raise ValueError("No IP addresses resolved")
    
    for ip in ip_addresses:
        if ip.startswith('127.') or ip.startswith('0.') or ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('169.254.'):
            raise ValueError("Disallowed private IP address")
        if ip.startswith('172.'):
            try:
                second_octet = int(ip.split('.')[1])
                if 16 <= second_octet <= 31:
                    raise ValueError("Disallowed private IP address")
            except (IndexError, ValueError):
                pass
        if ':' in ip:
            if ip == '::1' or ip.startswith('fc') or ip.startswith('fd') or ip.startswith('fe80:'):
                raise ValueError("Disallowed private IP address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects not followed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    if isinstance(body, bytes):
        return body.decode('utf-8')
    
    return str(body)
