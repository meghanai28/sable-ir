import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    redirect_count = 0
    
    def validate_url(parsed_url):
        scheme = parsed_url.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        if parsed_url.port is None:
            expected_port = 443 if scheme == 'https' else 80
        else:
            expected_port = parsed_url.port
        
        if (scheme == 'http' and expected_port != 80) or (scheme == 'https' and expected_port != 443):
            raise ValueError("Non-default port")
        
        if parsed_url.username is not None or parsed_url.password is not None:
            raise ValueError("Credentials not allowed")
        
        hostname = parsed_url.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        ip_addresses = resolve_host(hostname)
        
        for ip_str in ip_addresses:
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError("Invalid IP address from DNS")
            
            if isinstance(ip, ipaddress.IPv4Address):
                if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                    raise ValueError("Non-public IPv4 address")
                if ip.is_link_local:
                    raise ValueError("Non-public IPv4 address")
            elif isinstance(ip, ipaddress.IPv6Address):
                if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                    raise ValueError("Non-public IPv6 address")
                if ip.is_link_local:
                    raise ValueError("Non-public IPv6 address")
        
        return True
    
    def resolve_location(base_url, location):
        return urllib.parse.urljoin(base_url, location)
    
    current_url = url
    parsed = urllib.parse.urlparse(current_url)
    validate_url(parsed)
    
    while True:
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")
            
            current_url = resolve_location(current_url, location)
            parsed = urllib.parse.urlparse(current_url)
            validate_url(parsed)
            continue
        
        raise ValueError(f"Non-200 status: {status}")
