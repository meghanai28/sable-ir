import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    hop_count = 0
    
    def is_public_ip(ip_str):
        try:
            addr = ipaddress.ip_address(ip_str)
            return not (
                addr.is_private or
                addr.is_loopback or
                addr.is_link_local or
                addr.is_multicast or
                addr.is_reserved or
                addr.is_unspecified
            )
        except ValueError:
            return False
    
    def validate_url(url_str):
        try:
            parsed = urllib.parse.urlparse(url_str)
        except Exception:
            raise ValueError("Invalid URL")
        
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        if not parsed.hostname:
            raise ValueError("Missing hostname")
        
        default_port = 443 if parsed.scheme == 'https' else 80
        
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")
        
        hostname = parsed.hostname
        
        try:
            ip_addr = ipaddress.ip_address(hostname)
            if not is_public_ip(str(ip_addr)):
                raise ValueError("Non-public IP address")
            return url_str
        except ValueError:
            pass
        
        resolved_ips = resolve_host(hostname)
        if not resolved_ips:
            raise ValueError("Hostname resolution failed")
        
        for ip_str in resolved_ips:
            if not is_public_ip(ip_str):
                raise ValueError("Non-public IP address in DNS resolution")
        
        return url_str
    
    def resolve_location(base_url, location):
        if location is None:
            raise ValueError("Missing Location header")
        return urllib.parse.urljoin(base_url, location)
    
    current_url = validate_url(url)
    
    while True:
        if hop_count > MAX_REDIRECTS:
            raise ValueError("Too many redirects")
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            hop_count += 1
            if hop_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = None
            for key, value in headers.items() if isinstance(headers, dict) else headers:
                if key.lower() == 'location':
                    location = value
                    break
            
            current_url = validate_url(resolve_location(current_url, location))
            continue
        
        raise ValueError(f"Unexpected status: {status}")
