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
    query = parsed.query
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Host resolution failed")
    
    for addr_str in ip_addresses:
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            raise ValueError("Invalid IP address")
        
        if addr.is_loopback:
            raise ValueError("Non-public IP address")
        if addr.is_link_local:
            raise ValueError("Non-public IP address")
        if addr.is_private:
            raise ValueError("Non-public IP address")
        if getattr(addr, 'is_unique_local', False):
            raise ValueError("Non-public IP address")
        if addr.is_multicast:
            raise ValueError("Non-public IP address")
        if addr.is_reserved:
            raise ValueError("Non-public IP address")
        if addr.is_unspecified:
            raise ValueError("Non-public IP address")
        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
            ipv4 = addr.ipv4_mapped
            if ipv4.is_loopback or ipv4.is_link_local or ipv4.is_private or ipv4.is_multicast or ipv4.is_reserved or ipv4.is_unspecified:
                raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if status in (301, 302, 303, 307, 308):
        raise ValueError("Redirect not allowed")
    
    if status == 200:
        return body
    
    raise ValueError("Non-200 status code")
