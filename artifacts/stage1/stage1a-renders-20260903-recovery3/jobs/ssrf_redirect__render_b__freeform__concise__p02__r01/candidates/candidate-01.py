import ipaddress
import re
from urllib.parse import urlparse, urljoin

def _validate_scheme_port(parsed):
    scheme = parsed.scheme.lower()
    if scheme == 'http':
        expected_port = 80
    elif scheme == 'https':
        expected_port = 443
    else:
        raise ValueError("Invalid scheme")
    
    port = parsed.port
    if port is None:
        port = expected_port
    
    if port != expected_port:
        raise ValueError("Non-default port")
    
    return scheme, expected_port

def _validate_credentials(parsed):
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials not allowed")

def _is_public_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    
    if ip.is_private:
        return False
    if ip.is_loopback:
        return False
    if ip.is_link_local:
        return False
    if ip.is_multicast:
        return False
    if ip.is_reserved:
        return False
    if ip.is_unspecified:
        return False
    if hasattr(ip, 'is_site_local') and ip.is_site_local:
        return False
    
    return True

def _validate_hostname_ip(hostname, resolve_host):
    try:
        ip = ipaddress.ip_address(hostname)
        if not _is_public_ip(str(ip)):
            raise ValueError("Non-public IP")
        return [str(ip)]
    except ValueError:
        pass
    
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError("No DNS resolution")
    
    for ip_str in ips:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError("Invalid IP from DNS")
        
        if not _is_public_ip(ip_str):
            raise ValueError("Non-public IP from DNS")
    
    return ips

def _validate_url(url, resolve_host):
    parsed = urlparse(url)
    
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Invalid URL")
    
    scheme, expected_port = _validate_scheme_port(parsed)
    _validate_credentials(parsed)
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("No hostname")
    
    _validate_hostname_ip(hostname, resolve_host)
    
    return parsed

def _resolve_location(location, base_url):
    return urljoin(base_url, location)

def fetch_text(url, transport, resolve_host):
    current_url = url
    redirect_count = 0
    max_redirects = 5
    
    while True:
        parsed = _validate_url(current_url, resolve_host)
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if not location:
                raise ValueError("Redirect without Location")
            
            current_url = _resolve_location(location, current_url)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
