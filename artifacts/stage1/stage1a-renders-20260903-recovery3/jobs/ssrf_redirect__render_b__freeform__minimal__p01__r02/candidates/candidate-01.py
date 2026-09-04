import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    MAX_HOPS = 5
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
    
    def validate_url(parsed_url):
        scheme = parsed_url.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        default_port = 80 if scheme == 'http' else 443
        port = parsed_url.port
        if port is not None and port != default_port:
            raise ValueError("Non-default port not allowed")
        
        if parsed_url.username is not None or parsed_url.password is not None:
            raise ValueError("Userinfo not allowed")
        
        hostname = parsed_url.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        try:
            ip_addrs = resolve_host(hostname)
        except Exception:
            raise ValueError("DNS resolution failed")
        
        if not ip_addrs:
            raise ValueError("No IP addresses found")
        
        has_public = any(is_public_ip(addr) for addr in ip_addrs)
        if not has_public:
            raise ValueError("No public IP address found")
        
        return parsed_url
    
    def resolve_location(current_url, location):
        return urllib.parse.urljoin(current_url, location)
    
    current_url = url
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        validate_url(parsed)
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            hop_count += 1
            if hop_count > MAX_HOPS:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect without Location header")
            
            current_url = resolve_location(current_url, location)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
