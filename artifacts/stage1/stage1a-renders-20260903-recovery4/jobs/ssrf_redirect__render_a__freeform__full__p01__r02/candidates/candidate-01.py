import ipaddress
import re
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Userinfo not allowed")
    
    if parsed.fragment:
        raise ValueError("Fragment not allowed")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Empty hostname")
    
    default_port = 80 if scheme == 'http' else 443
    
    if parsed.port is not None:
        if parsed.port != default_port:
            raise ValueError("Non-default port not allowed")
        port = parsed.port
    else:
        port = default_port
    
    path = parsed.path if parsed.path else '/'
    query = '?' + parsed.query if parsed.query else ''
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Host resolution failed")
    
    for ip_str in ip_addresses:
        ip = ipaddress.ip_address(ip_str)
        
        if ip.is_loopback:
            raise ValueError("Non-public IP address")
        if ip.is_link_local:
            raise ValueError("Non-public IP address")
        if ip.is_private:
            raise ValueError("Non-public IP address")
        if isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local:
            raise ValueError("Non-public IP address")
        if ip.is_multicast:
            raise ValueError("Non-public IP address")
        if ip.is_reserved:
            raise ValueError("Non-public IP address")
        if ip.is_unspecified:
            raise ValueError("Non-public IP address")
        if hasattr(ip, 'is_global') and not ip.is_global:
            raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if status in (301, 302, 303, 307, 308):
        raise ValueError("Redirect not allowed")
    
    if status == 200:
        return body
    
    raise ValueError("Non-200 status code")
