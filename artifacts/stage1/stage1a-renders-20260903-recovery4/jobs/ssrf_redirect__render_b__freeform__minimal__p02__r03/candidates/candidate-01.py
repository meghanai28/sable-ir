import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    def is_public_ip(ip_str):
        try:
            ip = ipaddress.ip_address(ip_str)
            return ip.is_global
        except ValueError:
            return False
    
    def validate_and_fetch(current_url, redirect_count):
        if redirect_count > 5:
            raise ValueError("Too many redirects")
        
        parsed = urllib.parse.urlparse(current_url)
        
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        expected_port = 80 if scheme == 'http' else 443
        
        if parsed.port is not None and parsed.port != expected_port:
            raise ValueError("Non-default port")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Userinfo not allowed")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        ip_addresses = resolve_host(hostname)
        for ip in ip_addresses:
            if not is_public_ip(ip):
                raise ValueError("Non-public IP address")
        
        netloc = hostname
        reconstructed = urllib.parse.urlunparse((
            scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        
        status, headers, body = transport(reconstructed)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")
            
            new_url = urllib.parse.urljoin(current_url, location)
            return validate_and_fetch(new_url, redirect_count + 1)
        
        raise ValueError(f"Unexpected status: {status}")
    
    return validate_and_fetch(url, 0)
