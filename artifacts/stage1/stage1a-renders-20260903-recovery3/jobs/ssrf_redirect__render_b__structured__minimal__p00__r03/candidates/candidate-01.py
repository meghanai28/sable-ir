import ipaddress
import re
import urllib.parse

def _is_public_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
            or getattr(ip, 'is_site_local', False)
        )
    except ValueError:
        return False

def _validate_url(url):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    default_port = 443 if parsed.scheme == 'https' else 80
    port = parsed.port
    if port is None:
        port = default_port
    if port != default_port:
        raise ValueError("Invalid port")
    
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials not allowed")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    if not hostname:
        raise ValueError("Empty hostname")
    
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname) or re.match(r'^\[?[0-9a-fA-F:]+\]?$', hostname):
        try:
            ip = ipaddress.ip_address(hostname.strip('[]'))
            if not _is_public_ip(str(ip)):
                raise ValueError("Non-public IP address")
        except ValueError:
            raise ValueError("Invalid IP address")
    else:
        raise ValueError("Hostname must be resolved")
    
    return parsed

def _validate_resolved_url(url, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    default_port = 443 if parsed.scheme == 'https' else 80
    port = parsed.port
    if port is None:
        port = default_port
    if port != default_port:
        raise ValueError("Invalid port")
    
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials not allowed")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    if not hostname:
        raise ValueError("Empty hostname")
    
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname) or re.match(r'^\[?[0-9a-fA-F:]+\]?$', hostname):
        try:
            ip = ipaddress.ip_address(hostname.strip('[]'))
            if not _is_public_ip(str(ip)):
                raise ValueError("Non-public IP address")
        except ValueError:
            raise ValueError("Invalid IP address")
    else:
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("No DNS resolution")
        for ip_str in ips:
            if not _is_public_ip(ip_str):
                raise ValueError("Non-public IP address")
    
    return parsed

def fetch_text(url, transport, resolve_host):
    current_url = url
    
    _validate_resolved_url(current_url, resolve_host)
    
    for hop in range(5):
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")
            
            current_url = urllib.parse.urljoin(current_url, location)
            _validate_resolved_url(current_url, resolve_host)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
    
    raise ValueError("Too many redirects")
