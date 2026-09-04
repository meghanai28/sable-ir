import urllib.parse

def fetch_text(url, transport, resolve_host):
    max_hops = 5
    hop_count = 0
    current_url = url
    
    def validate_url(url_to_validate):
        parsed = urllib.parse.urlparse(url_to_validate)
        
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS schemes are allowed")
        
        if not parsed.hostname:
            raise ValueError("URL must have a hostname")
        
        default_port = 443 if parsed.scheme == 'https' else 80
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Only default ports are allowed")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials in URL are not allowed")
        
        ip_addresses = resolve_host(parsed.hostname)
        if not ip_addresses:
            raise ValueError("Hostname could not be resolved")
        
        return parsed
    
    def resolve_location(base_url, location):
        return urllib.parse.urljoin(base_url, location)
    
    parsed = validate_url(current_url)
    
    while True:
        if hop_count > max_hops:
            raise ValueError("Exceeded maximum redirect hops")
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            location = headers.get('Location')
            if not location:
                raise ValueError("Redirect response missing Location header")
            
            current_url = resolve_location(current_url, location)
            parsed = validate_url(current_url)
            hop_count += 1
            continue
        
        raise ValueError(f"Unexpected status code: {status}")
