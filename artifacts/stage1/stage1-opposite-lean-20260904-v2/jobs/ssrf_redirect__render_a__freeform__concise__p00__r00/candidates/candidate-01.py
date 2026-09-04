import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    visited = 0
    
    def validate_url(url_to_validate):
        parsed = urllib.parse.urlparse(url_to_validate)
        
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Scheme must be HTTP or HTTPS")
        
        default_port = 80 if parsed.scheme == 'http' else 443
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port specified")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("No hostname in URL")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed in URL")
        
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError("DNS resolution failed")
        
        for ip_str in ip_addresses:
            try:
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast or ip.is_link_local:
                    raise ValueError("Invalid destination address")
            except ValueError:
                raise ValueError("Invalid IP address from DNS")
        
        return parsed
    
    def resolve_location(current_url, location):
        return urllib.parse.urljoin(current_url, location)
    
    current_url = url
    
    while True:
        parsed = validate_url(current_url)
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            visited += 1
            if visited > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect without Location header")
            
            current_url = resolve_location(current_url, location)
            continue
        
        raise ValueError(f"Unexpected status code: {status}")
