import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    redirect_count = 0
    
    def validate_url(url_to_validate):
        parsed = urllib.parse.urlparse(url_to_validate)
        
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS schemes are allowed")
        
        default_port = 443 if parsed.scheme == 'https' else 80
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Only default ports are allowed")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials in URL are not allowed")
        
        if not parsed.hostname:
            raise ValueError("URL must have a hostname")
        
        return parsed
    
    def validate_ip_addresses(hostname):
        ips = resolve_host(hostname)
        
        if not ips:
            raise ValueError("No IP addresses resolved")
        
        for ip_str in ips:
            try:
                addr = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError(f"Invalid IP address: {ip_str}")
            
            if addr.is_loopback:
                raise ValueError("Loopback addresses are not allowed")
            if addr.is_multicast:
                raise ValueError("Multicast addresses are not allowed")
            if addr.is_reserved:
                raise ValueError("Reserved addresses are not allowed")
            if addr.is_private:
                raise ValueError("Private addresses are not allowed")
            if addr.is_link_local:
                raise ValueError("Link-local addresses are not allowed")
            if addr.is_unspecified:
                raise ValueError("Unspecified addresses are not allowed")
            if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
                mapped = addr.ipv4_mapped
                if mapped.is_loopback or mapped.is_private or mapped.is_reserved or mapped.is_multicast or mapped.is_link_local or mapped.is_unspecified:
                    raise ValueError("IPv4-mapped addresses with disallowed IPv4 equivalents are not allowed")
    
    def resolve_location(current_url, location):
        return urllib.parse.urljoin(current_url, location)
    
    current_url = url
    
    while True:
        parsed = validate_url(current_url)
        validate_ip_addresses(parsed.hostname)
        
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
        
        raise ValueError(f"Unexpected status code: {status}")
