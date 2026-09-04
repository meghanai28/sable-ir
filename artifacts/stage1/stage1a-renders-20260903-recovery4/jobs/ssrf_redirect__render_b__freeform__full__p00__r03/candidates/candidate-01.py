import ipaddress
from urllib.parse import urlparse, urljoin

def fetch_text(url, transport, resolve_host):
    def validate_url(target_url):
        parsed = urlparse(target_url)
        
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        default_port = 443 if parsed.scheme == 'https' else 80
        
        port = parsed.port
        if port is not None and port != default_port:
            raise ValueError("Non-default port not allowed")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError("DNS resolution failed")
        
        for addr in ip_addresses:
            try:
                ip = ipaddress.ip_address(addr)
                if ip.is_private:
                    raise ValueError("Private IP address not allowed")
                if ip.is_loopback:
                    raise ValueError("Loopback IP address not allowed")
                if ip.is_reserved:
                    raise ValueError("Reserved IP address not allowed")
                if ip.is_multicast:
                    raise ValueError("Multicast IP address not allowed")
                if ip.is_link_local:
                    raise ValueError("Link-local IP address not allowed")
                if ip.is_unspecified:
                    raise ValueError("Unspecified IP address not allowed")
            except ValueError:
                raise ValueError("Invalid IP address")
        
        return parsed.geturl()
    
    current_url = validate_url(url)
    redirect_hops = 0
    
    while True:
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 307, 308):
            redirect_hops += 1
            if redirect_hops > 5:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")
            
            redirect_url = urljoin(current_url, location)
            current_url = validate_url(redirect_url)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
