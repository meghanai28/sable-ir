import re
import ipaddress
from urllib.parse import urlparse, urljoin

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    redirect_count = 0
    
    def is_public_ip(addr):
        try:
            ip = ipaddress.ip_address(addr)
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
    
    def validate_and_fetch(current_url):
        nonlocal redirect_count
        
        parsed = urlparse(current_url)
        
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS schemes are allowed")
        
        port = parsed.port
        if port is None:
            port = 80 if scheme == 'http' else 443
        
        default_port = 80 if scheme == 'http' else 443
        if port != default_port:
            raise ValueError("Only default ports are allowed")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Userinfo in URL is not allowed")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("URL must have a hostname")
        
        ip_addresses = resolve_host(hostname)
        
        found_valid = False
        for addr in ip_addresses:
            try:
                ipaddress.ip_address(addr)
            except ValueError:
                raise ValueError(f"Invalid IP address returned: {addr}")
            
            if not is_public_ip(addr):
                raise ValueError(f"Non-public IP address not allowed: {addr}")
            found_valid = True
        
        if not found_valid:
            raise ValueError("No valid IP addresses found for hostname")
        
        sanitized_url = f"{scheme}://{hostname}"
        if parsed.path:
            sanitized_url += parsed.path
        else:
            sanitized_url += '/'
        if parsed.query:
            sanitized_url += '?' + parsed.query
        if parsed.fragment:
            sanitized_url += '#' + parsed.fragment
        
        status, headers, body = transport(sanitized_url)
        
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
                raise ValueError("Redirect response missing Location header")
            
            new_url = urljoin(current_url, location)
            return validate_and_fetch(new_url)
        
        if status == 200:
            if isinstance(body, bytes):
                return body.decode('utf-8', errors='replace')
            return str(body)
        
        raise ValueError(f"Unsupported HTTP status: {status}")
    
    return validate_and_fetch(url)
