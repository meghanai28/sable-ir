import urllib.parse

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    visited = 0
    
    def validate_url(parsed):
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        default_port = 80 if scheme == 'http' else 443
        port = parsed.port
        if port is not None and port != default_port:
            raise ValueError("Non-default port not allowed")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("DNS resolution failed")
        
        for ip in ips:
            if ip.startswith('127.') or ip.startswith('::1') or ip == '127.0.0.1':
                raise ValueError("Loopback address not allowed")
            if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
                if ip.startswith('172.'):
                    try:
                        second_octet = int(ip.split('.')[1])
                        if 16 <= second_octet <= 31:
                            raise ValueError("Private address not allowed")
                    except (IndexError, ValueError):
                        pass
                else:
                    raise ValueError("Private address not allowed")
            if ip.startswith('169.254.'):
                raise ValueError("Link-local address not allowed")
            if ip.startswith('0.') or ip == '0.0.0.0':
                raise ValueError("Invalid address not allowed")
            if ip.startswith('fc00:') or ip.startswith('fd00:'):
                raise ValueError("Unique local address not allowed")
            if ip.startswith('fe80:'):
                raise ValueError("Link-local address not allowed")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")
        
        return True
    
    def resolve_location(current_url, location):
        return urllib.parse.urljoin(current_url, location)
    
    current_url = url
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        validate_url(parsed)
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            visited += 1
            if visited > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = None
            for key, value in headers.items() if isinstance(headers, dict) else headers:
                if key.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Redirect without Location header")
            
            current_url = resolve_location(current_url, location)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
