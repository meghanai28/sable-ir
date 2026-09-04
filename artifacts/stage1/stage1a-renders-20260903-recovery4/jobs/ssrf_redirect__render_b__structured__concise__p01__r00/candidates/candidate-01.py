import urllib.parse

def fetch_text(url, transport, resolve_host):
    max_hops = 5
    current_url = url
    hops = 0
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Disallowed scheme")
        
        if parsed.scheme == 'http':
            default_port = 80
        else:
            default_port = 443
        
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Disallowed non-default port")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Disallowed credentials in URL")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        try:
            ips = resolve_host(hostname)
        except Exception:
            raise ValueError("DNS resolution failed")
        
        if not ips:
            raise ValueError("No IP addresses resolved")
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            hops += 1
            if hops > max_hops:
                raise ValueError("Redirect hop limit exceeded")
            
            location = None
            for key, value in headers:
                if key.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Missing Location header in redirect")
            
            current_url = urllib.parse.urljoin(current_url, location)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
