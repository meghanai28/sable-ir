import ipaddress
from urllib.parse import urlparse, urljoin

def fetch_text(url, transport, resolve_host):
    def validate_url(target_url):
        parsed = urlparse(target_url)
        
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        default_port = 80 if scheme == 'http' else 443
        
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port not allowed")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("No hostname")
        
        try:
            ip_addrs = resolve_host(hostname)
        except Exception:
            raise ValueError("DNS resolution failed")
        
        if not ip_addrs:
            raise ValueError("No IP addresses returned")
        
        for addr in ip_addrs:
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                raise ValueError("Invalid IP address")
            
            if ip.is_loopback:
                raise ValueError("Loopback address not allowed")
            if ip.is_link_local:
                raise ValueError("Link-local address not allowed")
            if ip.is_private:
                raise ValueError("Private address not allowed")
            if ip.is_multicast:
                raise ValueError("Multicast address not allowed")
            if ip.is_reserved:
                raise ValueError("Reserved address not allowed")
            if ip.is_unspecified:
                raise ValueError("Unspecified address not allowed")
        
        return target_url
    
    def is_redirect_status(status):
        return status in (301, 302, 303, 307, 308)
    
    current_url = url
    validate_url(current_url)
    
    hops = 0
    max_hops = 5
    
    while True:
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if is_redirect_status(status):
            hops += 1
            if hops > max_hops:
                raise ValueError("Too many redirects")
            
            location = None
            for key, value in headers.items() if isinstance(headers, dict) else headers:
                if key.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Redirect without Location header")
            
            current_url = urljoin(current_url, location)
            validate_url(current_url)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
