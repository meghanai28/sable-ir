import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    redirect_count = 0
    
    def validate_url(parsed):
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        default_port = 443 if parsed.scheme == 'https' else 80
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")
        
        if not parsed.hostname:
            raise ValueError("Missing hostname")
        
        return parsed.hostname, default_port
    
    def validate_ip_addresses(hostname):
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("No IP addresses resolved")
        
        for ip_str in ips:
            try:
                addr = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError("Invalid IP address")
            
            if addr.is_loopback:
                raise ValueError("Loopback address not allowed")
            if addr.is_multicast:
                raise ValueError("Multicast address not allowed")
            if addr.is_link_local:
                raise ValueError("Link-local address not allowed")
            if addr.is_unspecified:
                raise ValueError("Unspecified address not allowed")
            if addr.is_private:
                raise ValueError("Private address not allowed")
            if addr.is_reserved:
                raise ValueError("Reserved address not allowed")
            if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is None:
                if not addr.is_global:
                    raise ValueError("Non-global IPv6 address not allowed")
            elif isinstance(addr, ipaddress.IPv4Address):
                if not addr.is_global:
                    raise ValueError("Non-global IPv4 address not allowed")
        
        return ips
    
    def resolve_location(base_parsed, location):
        resolved = urllib.parse.urljoin(base_parsed.geturl(), location)
        parsed = urllib.parse.urlparse(resolved)
        return parsed
    
    current_url = url
    current_parsed = urllib.parse.urlparse(current_url)
    
    hostname, _ = validate_url(current_parsed)
    validate_ip_addresses(hostname)
    
    while True:
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = None
            for key, value in headers:
                if key.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Redirect without Location header")
            
            new_parsed = resolve_location(current_parsed, location)
            new_hostname, _ = validate_url(new_parsed)
            validate_ip_addresses(new_hostname)
            
            current_url = new_parsed.geturl()
            current_parsed = new_parsed
            
            if status == 303:
                current_parsed = current_parsed._replace(scheme='http')
                current_url = current_parsed.geturl()
                current_parsed = urllib.parse.urlparse(current_url)
                validate_url(current_parsed)
            
            continue
        
        raise ValueError(f"Unexpected status: {status}")
