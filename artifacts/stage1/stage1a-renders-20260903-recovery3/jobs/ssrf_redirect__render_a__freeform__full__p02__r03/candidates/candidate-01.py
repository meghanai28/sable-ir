import ipaddress
import re
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    
    scheme = parsed.scheme
    if scheme not in ('http', 'https'):
        raise ValueError
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError
    
    port = parsed.port
    
    if scheme == 'http':
        if port is not None and port != 80:
            raise ValueError
    elif scheme == 'https':
        if port is not None and port != 443:
            raise ValueError
    
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError
    
    for addr_str in ip_addresses:
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            raise ValueError
        
        if addr.is_private:
            raise ValueError
        if addr.is_loopback:
            raise ValueError
        if addr.is_link_local:
            raise ValueError
        if addr.is_multicast:
            raise ValueError
        if addr.is_reserved:
            raise ValueError
        if isinstance(addr, ipaddress.IPv6Address):
            if addr.is_site_local:
                raise ValueError
            if addr.ipv4_mapped is not None:
                ipv4_addr = addr.ipv4_mapped
                if ipv4_addr.is_private or ipv4_addr.is_loopback or ipv4_addr.is_link_local or ipv4_addr.is_multicast or ipv4_addr.is_reserved:
                    raise ValueError
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError
    
    if status != 200:
        raise ValueError
    
    return body
