import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    redirect_count = 0
    
    def validate_url(parsed_url):
        if parsed_url.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        if parsed_url.port is not None:
            default_port = 443 if parsed_url.scheme == 'https' else 80
            if parsed_url.port != default_port:
                raise ValueError("Non-default port")
        
        if parsed_url.username is not None or parsed_url.password is not None:
            raise ValueError("Credentials not allowed")
        
        if not parsed_url.hostname:
            raise ValueError("Missing hostname")
        
        return parsed_url.hostname
    
    def validate_ip_addresses(hostname):
        ip_addresses = resolve_host(hostname)
        
        if not ip_addresses:
            raise ValueError("No IP addresses resolved")
        
        for ip_str in ip_addresses:
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError("Invalid IP address")
            
            if ip.is_loopback:
                raise ValueError("Loopback address not allowed")
            if ip.is_multicast:
                raise ValueError("Multicast address not allowed")
            if ip.is_reserved:
                raise ValueError("Reserved address not allowed")
            if ip.is_private:
                raise ValueError("Private address not allowed")
            if ip.is_link_local:
                raise ValueError("Link-local address not allowed")
            if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is None:
                if ip.is_site_local:
                    raise ValueError("Site-local address not allowed")
    
    def resolve_location(current_url, location):
        return urllib.parse.urljoin(current_url, location)
    
    current_url = url
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        hostname = validate_url(parsed)
        validate_ip_addresses(hostname)
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if not location:
                raise ValueError("Redirect without Location header")
            
            current_url = resolve_location(current_url, location)
            continue
        
        raise ValueError(f"Non-200 status: {status}")
