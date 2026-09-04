import urllib.parse

def fetch_text(url, transport, resolve_host):
    MAX_HOPS = 5
    current_url = url
    hops = 0
    
    def validate_url(url_to_validate):
        parsed = urllib.parse.urlparse(url_to_validate)
        
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS schemes are allowed")
        
        if parsed.scheme == 'http' and parsed.port is not None and parsed.port != 80:
            raise ValueError("HTTP must use default port 80")
        if parsed.scheme == 'https' and parsed.port is not None and parsed.port != 443:
            raise ValueError("HTTPS must use default port 443")
        
        if not parsed.hostname:
            raise ValueError("URL must have a hostname")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials in URL are not allowed")
        
        ip_addresses = resolve_host(parsed.hostname)
        if not ip_addresses:
            raise ValueError("Hostname could not be resolved")
        
        return parsed
    
    def resolve_location(base_url, location):
        if location is None:
            raise ValueError("Redirect without Location header")
        return urllib.parse.urljoin(base_url, location)
    
    parsed = validate_url(current_url)
    
    while True:
        if hops > MAX_HOPS:
            raise ValueError("Exceeded maximum redirect hops")
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            location = headers.get('Location')
            current_url = resolve_location(current_url, location)
            parsed = validate_url(current_url)
            hops += 1
            continue
        
        raise ValueError(f"Unexpected status code: {status}")
