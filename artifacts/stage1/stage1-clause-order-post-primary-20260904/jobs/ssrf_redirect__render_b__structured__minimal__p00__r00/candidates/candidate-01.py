import urllib.parse

def fetch_text(url, transport, resolve_host):
    current_url = url
    hops = 0
    max_hops = 5
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("disallowed request: invalid scheme")
        
        default_port = 443 if parsed.scheme == 'https' else 80
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("disallowed request: non-default port")
        
        if not parsed.hostname:
            raise ValueError("disallowed request: missing hostname")
        
        try:
            ips = resolve_host(parsed.hostname)
        except Exception:
            raise ValueError("disallowed request: DNS resolution failed")
        
        if not ips:
            raise ValueError("disallowed request: no IP addresses resolved")
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            hops += 1
            if hops >= max_hops:
                raise ValueError("disallowed request: redirect limit exceeded")
            
            location = headers.get('Location')
            if not location:
                raise ValueError("disallowed request: missing Location header")
            
            current_url = urllib.parse.urljoin(current_url, location)
            continue
        
        raise ValueError("disallowed request: non-success status")
