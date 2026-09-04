import re
import ipaddress
from urllib.parse import urlparse, urljoin, urlunparse

def fetch_text(url, transport, resolve_host):
    def validate_url(parsed):
        if not parsed.scheme:
            raise ValueError("Missing scheme")
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS are allowed")
        
        default_port = 443 if parsed.scheme == 'https' else 80
        
        port = parsed.port
        if port is None:
            port = default_port
        
        if port != default_port:
            raise ValueError("Non-default port not allowed")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Userinfo not allowed")
        
        if not parsed.hostname:
            raise ValueError("Missing hostname")
        
        return parsed.hostname, port
    
    def is_public_ip(addr_str):
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            return False
        
        if addr.is_loopback:
            return False
        if addr.is_private:
            return False
        if addr.is_reserved:
            return False
        if addr.is_multicast:
            return False
        if addr.is_link_local:
            return False
        if addr.version == 4 and addr.is_unspecified:
            return False
        if addr.version == 6 and addr == ipaddress.IPv6Address('::'):
            return False
        
        return True
    
    def validate_host(hostname):
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("No IP addresses resolved")
        
        for ip_str in ips:
            try:
                ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError(f"Invalid IP address: {ip_str}")
            
            if not is_public_ip(ip_str):
                raise ValueError(f"Non-public IP address: {ip_str}")
        
        return ips
    
    def sanitize_url(parsed):
        netloc = parsed.hostname
        default_port = 443 if parsed.scheme == 'https' else 80
        if parsed.port is not None and parsed.port != default_port:
            netloc = f"{parsed.hostname}:{parsed.port}"
        
        sanitized = urlunparse((
            parsed.scheme,
            netloc,
            parsed.path or '/',
            parsed.params,
            parsed.query,
            ''
        ))
        return sanitized
    
    def do_fetch(current_url, redirect_count):
        if redirect_count > 5:
            raise ValueError("Too many redirects")
        
        parsed = urlparse(current_url)
        
        hostname, port = validate_url(parsed)
        validate_host(hostname)
        
        sanitized = sanitize_url(parsed)
        
        status, headers, body = transport(sanitized)
        
        if 300 <= status < 400:
            location = headers.get('Location')
            if not location:
                raise ValueError("Redirect without Location header")
            
            new_url = urljoin(current_url, location)
            new_parsed = urlparse(new_url)
            
            new_hostname, new_port = validate_url(new_parsed)
            validate_host(new_hostname)
            
            return do_fetch(new_url, redirect_count + 1)
        
        if status == 200:
            if isinstance(body, bytes):
                return body.decode('utf-8', errors='replace')
            return str(body)
        
        raise ValueError(f"Unsupported status: {status}")
    
    return do_fetch(url, 0)
