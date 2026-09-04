import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    def validate_url(parsed_url):
        scheme = parsed_url.scheme
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
        
        if '@' in parsed_url.netloc:
            userinfo = parsed_url.netloc.rsplit('@', 1)[0]
            if userinfo:
                raise ValueError("Credentials not allowed in URL")
        
        return hostname
    
    def validate_ip_addresses(hostname):
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError("DNS resolution failed: no addresses returned")
        
        for ip_str in ip_addresses:
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError(f"Invalid IP address from DNS: {ip_str}")
            
            if ip.is_loopback:
                raise ValueError("Loopback address not allowed")
            if ip.is_multicast:
                raise ValueError("Multicast address not allowed")
            if ip.is_link_local:
                raise ValueError("Link-local address not allowed")
            if isinstance(ip, ipaddress.IPv4Address):
                if ip.is_private:
                    raise ValueError("Private address not allowed")
                if ip.is_reserved:
                    raise ValueError("Reserved address not allowed")
                if ip == ipaddress.IPv4Address('0.0.0.0'):
                    raise ValueError("Unspecified address not allowed")
            elif isinstance(ip, ipaddress.IPv6Address):
                if ip.is_private:
                    raise ValueError("Private address not allowed")
                if ip.is_reserved:
                    raise ValueError("Reserved address not allowed")
                if ip == ipaddress.IPv6Address('::'):
                    raise ValueError("Unspecified address not allowed")
        
        return ip_addresses
    
    def make_request(request_url):
        parsed = urllib.parse.urlparse(request_url)
        hostname = validate_url(parsed)
        validate_ip_addresses(hostname)
        return transport(request_url)
    
    current_url = url
    hops = 0
    max_hops = 5
    
    while True:
        if hops >= max_hops:
            raise ValueError("Redirect hop limit exceeded")
        
        status, headers, body = make_request(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            hops += 1
            if hops >= max_hops:
                raise ValueError("Redirect hop limit exceeded")
            
            location = None
            for name, value in headers:
                if name.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Redirect response missing Location header")
            
            current_url = urllib.parse.urljoin(current_url, location)
            continue
        
        raise ValueError(f"Unexpected response status: {status}")
