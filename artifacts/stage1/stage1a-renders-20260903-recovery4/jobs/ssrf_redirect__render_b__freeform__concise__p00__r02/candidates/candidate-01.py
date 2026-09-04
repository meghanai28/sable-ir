import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    def validate_url(parsed_url):
        scheme = parsed_url.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Scheme must be HTTP or HTTPS")
        
        port = parsed_url.port
        if scheme == 'http' and port is not None and port != 80:
            raise ValueError("HTTP must use default port 80")
        if scheme == 'https' and port is not None and port != 443:
            raise ValueError("HTTPS must use default port 443")
        
        hostname = parsed_url.hostname
        if hostname is None:
            raise ValueError("URL must have a hostname")
        
        return scheme, hostname
    
    def validate_host(hostname):
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError("DNS resolution failed")
        
        for ip_str in ip_addresses:
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError("Invalid IP address from DNS")
            
            if ip.is_loopback:
                raise ValueError("Loopback address not allowed")
            if ip.is_private:
                raise ValueError("Private address not allowed")
            if ip.is_reserved:
                raise ValueError("Reserved address not allowed")
            if ip.is_multicast:
                raise ValueError("Multicast address not allowed")
            if ip.is_link_local:
                raise ValueError("Link-local address not allowed")
            if ip.version == 4 and ip.is_unspecified:
                raise ValueError("Unspecified address not allowed")
            if ip.version == 6 and ip == ipaddress.IPv6Address('::'):
                raise ValueError("Unspecified address not allowed")
        
        return ip_addresses
    
    def check_credentials(parsed_url):
        if parsed_url.username is not None or parsed_url.password is not None:
            raise ValueError("Credentials in URL not allowed")
    
    def resolve_location(current_url, location):
        return urllib.parse.urljoin(current_url, location)
    
    def make_request(request_url):
        parsed = urllib.parse.urlparse(request_url)
        scheme, hostname = validate_url(parsed)
        check_credentials(parsed)
        validate_host(hostname)
        return transport(request_url)
    
    current_url = url
    hops = 0
    max_hops = 5
    
    while True:
        if hops > max_hops:
            raise ValueError("Redirect hop limit exceeded")
        
        status, headers, body = make_request(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            hops += 1
            if hops > max_hops:
                raise ValueError("Redirect hop limit exceeded")
            
            location = None
            for key, value in headers:
                if key.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Redirect response missing Location header")
            
            current_url = resolve_location(current_url, location)
            continue
        
        raise ValueError(f"Unexpected status code: {status}")
