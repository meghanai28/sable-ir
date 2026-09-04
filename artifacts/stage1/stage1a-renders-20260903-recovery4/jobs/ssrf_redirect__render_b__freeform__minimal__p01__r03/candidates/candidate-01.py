import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    
    def validate_url(parsed_url):
        if parsed_url.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        if parsed_url.port is not None:
            default_port = 443 if parsed_url.scheme == 'https' else 80
            if parsed_url.port != default_port:
                raise ValueError("Non-default port")
        
        if parsed_url.username is not None or parsed_url.password is not None:
            raise ValueError("Userinfo not allowed")
        
        if not parsed_url.hostname:
            raise ValueError("Missing hostname")
        
        try:
            ip_addresses = resolve_host(parsed_url.hostname)
        except Exception:
            raise ValueError("DNS resolution failed")
        
        if not ip_addresses:
            raise ValueError("No IP addresses found")
        
        has_public = False
        for addr in ip_addresses:
            try:
                ip = ipaddress.ip_address(addr)
                if ip.is_global:
                    has_public = True
                    break
            except ValueError:
                continue
        
        if not has_public:
            raise ValueError("No public IP address")
        
        return True
    
    def resolve_location(current_url, location):
        return urllib.parse.urljoin(current_url, location)
    
    current_url = url
    hops = 0
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        validate_url(parsed)
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            hops += 1
            if hops > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if not location:
                raise ValueError("Redirect without Location header")
            
            current_url = resolve_location(current_url, location)
            continue
        
        raise ValueError(f"Non-200 status: {status}")
