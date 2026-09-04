import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    redirect_count = 0
    
    def validate_url(parsed):
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        port = parsed.port
        if port is None:
            port = 80 if scheme == 'http' else 443
        
        default_port = 80 if scheme == 'http' else 443
        if port != default_port:
            raise ValueError("Non-default port")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Userinfo not allowed")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        return scheme, port, hostname
    
    def validate_ip(ip_str):
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError("Invalid IP address")
        
        if addr.version == 4:
            if addr.is_private:
                raise ValueError("Private IPv4 address")
            if addr.is_loopback:
                raise ValueError("Loopback IPv4 address")
            if addr.is_link_local:
                raise ValueError("Link-local IPv4 address")
            if addr.is_multicast:
                raise ValueError("Multicast IPv4 address")
            if addr.is_reserved:
                raise ValueError("Reserved IPv4 address")
            if addr.is_unspecified:
                raise ValueError("Unspecified IPv4 address")
            if addr == ipaddress.IPv4Address('0.0.0.0'):
                raise ValueError("Zero IPv4 address")
        elif addr.version == 6:
            if addr.is_private:
                raise ValueError("Private IPv6 address")
            if addr.is_loopback:
                raise ValueError("Loopback IPv6 address")
            if addr.is_link_local:
                raise ValueError("Link-local IPv6 address")
            if addr.is_multicast:
                raise ValueError("Multicast IPv6 address")
            if addr.is_reserved:
                raise ValueError("Reserved IPv6 address")
            if addr.is_unspecified:
                raise ValueError("Unspecified IPv6 address")
        
        return True
    
    def resolve_and_validate(hostname):
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("No DNS resolution")
        for ip in ips:
            validate_ip(ip)
        return ips
    
    def build_sanitized_url(parsed, scheme):
        netloc = parsed.hostname
        if parsed.port is not None:
            default_port = 80 if scheme == 'http' else 443
            if parsed.port != default_port:
                netloc += ':' + str(parsed.port)
        
        path = parsed.path
        if not path:
            path = '/'
        
        params = parsed.params
        query = parsed.query
        fragment = ''
        
        sanitized = urllib.parse.urlunsplit((scheme, netloc, path, query, fragment))
        return sanitized
    
    current_url = url
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        scheme, port, hostname = validate_url(parsed)
        resolve_and_validate(hostname)
        sanitized = build_sanitized_url(parsed, scheme)
        
        status, headers, body = transport(sanitized)
        
        if status == 200:
            if isinstance(body, bytes):
                return body.decode('utf-8')
            return str(body)
        
        if 300 <= status < 400:
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = None
            for key, value in headers.items() if isinstance(headers, dict) else headers:
                if key.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Missing Location header")
            
            current_url = urllib.parse.urljoin(sanitized, location)
            continue
        
        raise ValueError("Unsupported status: {}".format(status))
