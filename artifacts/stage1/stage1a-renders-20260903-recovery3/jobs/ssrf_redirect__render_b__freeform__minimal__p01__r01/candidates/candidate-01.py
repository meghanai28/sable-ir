import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    
    def is_public_ip(ip_str):
        try:
            ip = ipaddress.ip_address(ip_str)
            return not (
                ip.is_private or
                ip.is_loopback or
                ip.is_link_local or
                ip.is_multicast or
                ip.is_reserved or
                ip.is_unspecified
            )
        except ValueError:
            return False
    
    def validate_url(url_str):
        parsed = urllib.parse.urlparse(url_str)
        
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Scheme must be HTTP or HTTPS")
        
        default_port = 80 if parsed.scheme == 'http' else 443
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Port must be the scheme's default")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Userinfo not allowed")
        
        if not parsed.hostname:
            raise ValueError("Hostname required")
        
        try:
            ip_addrs = resolve_host(parsed.hostname)
        except Exception:
            raise ValueError("DNS resolution failed")
        
        if not ip_addrs:
            raise ValueError("DNS resolution yielded no addresses")
        
        has_public = any(is_public_ip(addr) for addr in ip_addrs)
        if not has_public:
            raise ValueError("No public IP addresses found")
        
        return parsed
    
    def resolve_location(current_url, location):
        return urllib.parse.urljoin(current_url, location)
    
    current_url = url
    hops = 0
    
    while True:
        parsed = validate_url(current_url)
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            hops += 1
            if hops > MAX_REDIRECTS:
                raise ValueError("Redirect hop limit exceeded")
            
            location = None
            for header_name, header_value in headers:
                if header_name.lower() == 'location':
                    location = header_value
                    break
            
            if location is None:
                raise ValueError("Redirect response missing Location header")
            
            current_url = resolve_location(current_url, location)
            continue
        
        raise ValueError(f"Non-200 final status: {status}")
