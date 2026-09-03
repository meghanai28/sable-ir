import urllib.parse

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    default_port = 443 if parsed.scheme == 'https' else 80
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Non-default port not allowed")
    
    if not parsed.hostname:
        raise ValueError("URL must have a hostname")
    
    ip_addresses = resolve_host(parsed.hostname)
    if not ip_addresses:
        raise ValueError("Host resolution failed")
    
    for ip in ip_addresses:
        if ip.startswith('127.') or ip.startswith('10.') or ip.startswith('192.168.') or \
           (ip.startswith('172.') and 16 <= int(ip.split('.')[1]) <= 31) or \
           ip == '::1' or ip == '0.0.0.0':
            raise ValueError("Private or loopback address not allowed")
    
    current_url = url
    redirects = 0
    
    while True:
        parsed_current = urllib.parse.urlparse(current_url)
        
        if parsed_current.scheme not in ('http', 'https'):
            raise ValueError("Redirect to non-HTTP/HTTPS scheme not allowed")
        
        current_default_port = 443 if parsed_current.scheme == 'https' else 80
        if parsed_current.port is not None and parsed_current.port != current_default_port:
            raise ValueError("Redirect to non-default port not allowed")
        
        if not parsed_current.hostname:
            raise ValueError("Redirect URL must have a hostname")
        
        current_ips = resolve_host(parsed_current.hostname)
        if not current_ips:
            raise ValueError("Redirect host resolution failed")
        
        for ip in current_ips:
            if ip.startswith('127.') or ip.startswith('10.') or ip.startswith('192.168.') or \
               (ip.startswith('172.') and 16 <= int(ip.split('.')[1]) <= 31) or \
               ip == '::1' or ip == '0.0.0.0':
                raise ValueError("Redirect to private or loopback address not allowed")
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            redirects += 1
            if redirects > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location') or headers.get('location')
            if not location:
                raise ValueError("Redirect response missing Location header")
            
            current_url = urllib.parse.urljoin(current_url, location)
            continue
        
        raise ValueError(f"Unexpected status code: {status}")
