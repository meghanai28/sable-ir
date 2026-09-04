import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    def validate_url(parsed_url):
        if parsed_url.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        default_port = 443 if parsed_url.scheme == 'https' else 80
        port = parsed_url.port
        if port is not None and port != default_port:
            raise ValueError("Non-default port not allowed")
        
        if parsed_url.username is not None or parsed_url.password is not None:
            raise ValueError("Credentials not allowed")
        
        if not parsed_url.hostname:
            raise ValueError("Missing hostname")
        
        return parsed_url.hostname, default_port
    
    def validate_ip_addresses(hostname):
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("No IP addresses resolved")
        
        for ip_str in ips:
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError("Invalid IP address")
            
            if ip.version == 6:
                raise ValueError("IPv6 not allowed")
            
            if ip.is_loopback:
                raise ValueError("Loopback address not allowed")
            if ip.is_multicast:
                raise ValueError("Multicast address not allowed")
            if ip.is_link_local:
                raise ValueError("Link-local address not allowed")
            if ip.is_private:
                raise ValueError("Private address not allowed")
            if ip.is_reserved:
                raise ValueError("Reserved address not allowed")
            if ip.is_unspecified:
                raise ValueError("Unspecified address not allowed")
    
    def resolve_location(current_url, location):
        return urllib.parse.urljoin(current_url, location)
    
    current_url = url
    hops = 0
    max_hops = 5
    visited = set()
    
    while True:
        if hops > max_hops:
            raise ValueError("Too many redirects")
        
        if current_url in visited:
            raise ValueError("Redirect loop detected")
        visited.add(current_url)
        
        parsed = urllib.parse.urlparse(current_url)
        hostname, default_port = validate_url(parsed)
        validate_ip_addresses(hostname)
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            hops += 1
            if hops > max_hops:
                raise ValueError("Too many redirects")
            
            location = None
            for name, value in headers:
                if name.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Redirect without Location header")
            
            current_url = resolve_location(current_url, location)
            parsed_redirect = urllib.parse.urlparse(current_url)
            validate_url(parsed_redirect)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
