import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    
    def is_public_ip(ip_str):
        try:
            addr = ipaddress.ip_address(ip_str)
            return not (
                addr.is_loopback or
                addr.is_private or
                addr.is_reserved or
                addr.is_multicast or
                addr.is_link_local or
                getattr(addr, 'is_site_local', False)
            )
        except ValueError:
            return False
    
    def validate_url(parsed):
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Scheme must be http or https")
        
        default_port = 80 if parsed.scheme == 'http' else 443
        
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Port must be the default for the scheme")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Userinfo not allowed")
        
        if not parsed.hostname:
            raise ValueError("Hostname required")
        
        try:
            ip_addresses = resolve_host(parsed.hostname)
        except Exception:
            raise ValueError("DNS resolution failed")
        
        if not ip_addresses:
            raise ValueError("DNS resolution yielded no addresses")
        
        has_public = False
        for ip_str in ip_addresses:
            if is_public_ip(ip_str):
                has_public = True
                break
        
        if not has_public:
            raise ValueError("No public IP addresses found")
        
        return True
    
    def make_url_string(parsed):
        port = parsed.port
        default_port = 80 if parsed.scheme == 'http' else 443
        netloc = parsed.hostname
        if port is not None and port != default_port:
            netloc = f"{parsed.hostname}:{port}"
        return urllib.parse.urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
    
    current_url = url
    hops = 0
    
    while hops <= MAX_REDIRECTS:
        parsed = urllib.parse.urlparse(current_url)
        validate_url(parsed)
        
        url_to_fetch = make_url_string(parsed)
        status, headers, body = transport(url_to_fetch)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            hops += 1
            if hops > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = None
            for name, value in headers:
                if name.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Redirect without Location header")
            
            current_url = urllib.parse.urljoin(current_url, location)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
    
    raise ValueError("Too many redirects")
