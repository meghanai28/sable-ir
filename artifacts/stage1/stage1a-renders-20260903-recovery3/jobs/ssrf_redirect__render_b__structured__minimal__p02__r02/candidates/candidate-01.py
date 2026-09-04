import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    
    def is_public_ip(ip_str):
        try:
            ip = ipaddress.ip_address(ip_str)
            return not (
                ip.is_private or
                ip.is_loopback or
                ip.is_link_local or
                ip.is_multicast or
                ip.is_reserved or
                ip.is_unspecified
            )
        except ValueError:
            return False
    
    def validate_url(parsed_url):
        scheme = parsed_url.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Disallowed URL scheme")
        
        if scheme == 'http':
            default_port = 80
        else:
            default_port = 443
        
        port = parsed_url.port
        if port is None:
            port = default_port
        
        if port != default_port:
            raise ValueError("Disallowed non-default port")
        
        hostname = parsed_url.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        if '@' in parsed_url.netloc:
            userinfo = parsed_url.netloc.rsplit('@', 1)[0]
            if userinfo:
                raise ValueError("Disallowed credentials in URL")
        
        ip_addrs = resolve_host(hostname)
        if not ip_addrs:
            raise ValueError("Hostname resolution failed")
        
        for ip_str in ip_addrs:
            try:
                ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError("Invalid IP address from DNS")
        
        public_ips = [ip for ip in ip_addrs if is_public_ip(ip)]
        if not public_ips:
            raise ValueError("No public IP addresses found")
        
        return scheme, hostname, port
    
    def resolve_location(current_parsed, location):
        if location is None:
            raise ValueError("Missing Location header for redirect")
        
        new_url = urllib.parse.urljoin(current_parsed.geturl(), location)
        new_parsed = urllib.parse.urlparse(new_url)
        return new_parsed
    
    current_url = url
    redirects = 0
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        
        scheme, hostname, port = validate_url(parsed)
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            if redirects >= MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location') if isinstance(headers, dict) else None
            if location is None:
                if isinstance(headers, (list, tuple)):
                    for key, value in headers:
                        if key.lower() == 'location':
                            location = value
                            break
            
            new_parsed = resolve_location(parsed, location)
            validate_url(new_parsed)
            
            current_url = new_parsed.geturl()
            redirects += 1
            continue
        
        raise ValueError(f"Unsupported HTTP status: {status}")
