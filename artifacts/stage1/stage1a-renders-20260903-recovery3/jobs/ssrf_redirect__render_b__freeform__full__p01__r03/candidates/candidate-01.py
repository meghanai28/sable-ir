import ipaddress
from urllib.parse import urlparse, urljoin

def fetch_text(url, transport, resolve_host):
    def validate_url(target_url):
        parsed = urlparse(target_url)
        
        # Scheme validation
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        # Port validation
        default_port = 80 if parsed.scheme == 'http' else 443
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port")
        
        # Credential validation
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")
        
        # Hostname validation
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("No hostname")
        
        # DNS validation
        try:
            ip_addresses = resolve_host(hostname)
        except Exception:
            raise ValueError("DNS resolution failed")
        
        if not ip_addresses:
            raise ValueError("No IP addresses returned")
        
        # Public-address validation
        for ip_str in ip_addresses:
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError("Invalid IP address")
            
            if ip.is_loopback:
                raise ValueError("Loopback address")
            if ip.is_link_local:
                raise ValueError("Link-local address")
            if ip.is_private:
                raise ValueError("Private address")
            if ip.is_multicast:
                raise ValueError("Multicast address")
            if ip.is_reserved:
                raise ValueError("Reserved address")
            if ip.is_unspecified:
                raise ValueError("Unspecified address")
        
        return True
    
    def is_redirect_status(status):
        return status in (301, 302, 303, 307, 308)
    
    current_url = url
    hop_count = 0
    max_hops = 5
    
    while True:
        validate_url(current_url)
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if is_redirect_status(status):
            hop_count += 1
            if hop_count > max_hops:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")
            
            current_url = urljoin(current_url, location)
        else:
            raise ValueError("Invalid status")
