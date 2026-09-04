import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if parsed.scheme == 'http' and parsed.port is not None and parsed.port != 80:
        raise ValueError("HTTP must use default port 80")
    if parsed.scheme == 'https' and parsed.port is not None and parsed.port != 443:
        raise ValueError("HTTPS must use default port 443")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("URL must have a hostname")
    
    if hostname.startswith('[') and hostname.endswith(']'):
        raise ValueError("IPv6 literals not supported")
    
    try:
        ips = resolve_host(hostname)
    except Exception:
        raise ValueError("Could not resolve hostname")
    
    if not ips:
        raise ValueError("Hostname resolved to no addresses")
    
    for ip in ips:
        if ip.startswith('127.') or ip == '::1' or ip == '0.0.0.0':
            raise ValueError("Private or loopback addresses not allowed")
        if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
            if ip.startswith('172.'):
                try:
                    second_octet = int(ip.split('.')[1])
                    if 16 <= second_octet <= 31:
                        raise ValueError("Private addresses not allowed")
                except (ValueError, IndexError):
                    pass
            else:
                raise ValueError("Private addresses not allowed")
        if ip.startswith('169.254.'):
            raise ValueError("Link-local addresses not allowed")
        if ip.startswith('fc') or ip.startswith('fd'):
            raise ValueError("Unique local addresses not allowed")
        if ip == '::' or ip.startswith('fe80:'):
            raise ValueError("Special addresses not allowed")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects are not allowed")
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
