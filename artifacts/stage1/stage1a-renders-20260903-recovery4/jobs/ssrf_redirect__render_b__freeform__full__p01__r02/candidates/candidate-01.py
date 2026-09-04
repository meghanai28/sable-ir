import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    def validate_url(url_to_validate):
        parsed = urllib.parse.urlparse(url_to_validate)
        
        # Scheme validation
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        # Port validation
        default_port = 80 if parsed.scheme == 'http' else 443
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port not allowed")
        
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
                raise ValueError("Loopback address not allowed")
            if ip.is_link_local:
                raise ValueError("Link-local address not allowed")
            if ip.is_private:
                raise ValueError("Private address not allowed")
            if ip.is_multicast:
                raise ValueError("Multicast address not allowed")
            # Check for unspecified address
            if ip.is_unspecified:
                raise ValueError("Unspecified address not allowed")
            # Check for reserved addresses
            if ip.is_reserved:
                raise ValueError("Reserved address not allowed")
        
        return url_to_validate
    
    def is_redirect_status(status):
        return status in (301, 302, 303, 307, 308)
    
    current_url = validate_url(url)
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
            
            # Get Location header
            location = None
            for header_name, header_value in headers:
                if header_name.lower() == 'location':
                    location = header_value
                    break
            
            if location is None:
                raise ValueError("Redirect without Location header")
            
            # Resolve Location against current URL
            current_url = urllib.parse.urljoin(current_url, location)
            current_url = validate_url(current_url)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
