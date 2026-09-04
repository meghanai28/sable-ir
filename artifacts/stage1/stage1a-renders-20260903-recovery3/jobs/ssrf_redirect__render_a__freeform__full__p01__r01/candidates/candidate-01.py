import ipaddress
import re
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Scheme must be http or https")
    
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Userinfo not allowed")
    
    if parsed.fragment:
        raise ValueError("Fragment not allowed")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Hostname required")
    
    default_port = 80 if scheme == 'http' else 443
    
    if parsed.port is not None:
        if parsed.port != default_port:
            raise ValueError("Non-default port not allowed")
        port = parsed.port
    else:
        port = default_port
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Host resolution failed")
    
    if not ip_addresses:
        raise ValueError("Host resolution yielded no addresses")
    
    for addr_str in ip_addresses:
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            raise ValueError("Invalid IP address from resolution")
        
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
        
        if isinstance(addr, ipaddress.IPv6Address):
            if addr.ipv4_mapped is not None:
                mapped = addr.ipv4_mapped
                if mapped.is_loopback or mapped.is_link_local or mapped.is_private or mapped.is_multicast or mapped.is_reserved or mapped.is_unspecified:
                    raise ValueError("Non-public IP address")
            if (addr >> 32) == 0x20010db8:
                raise ValueError("Non-public IP address")
            if (addr >> 16) == 0x2002:
                raise ValueError("Non-public IP address")
            if (addr >> 32) == 0x5f00:
                raise ValueError("Non-public IP address")
            if (addr >> 96) == 0x64ff9b:
                raise ValueError("Non-public IP address")
            if (addr >> 32) == 0x100:
                raise ValueError("Non-public IP address")
            if addr == ipaddress.IPv6Address('2001:1::1'):
                raise ValueError("Non-public IP address")
            if addr == ipaddress.IPv6Address('2001:1::2'):
                raise ValueError("Non-public IP address")
            if (addr >> 32) == 0x20010001:
                raise ValueError("Non-public IP address")
            if (addr >> 16) == 0x3ffe:
                raise ValueError("Non-public IP address")
            if addr == ipaddress.IPv6Address('::'):
                raise ValueError("Non-public IP address")
            if addr == ipaddress.IPv6Address('::1'):
                raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if status in (301, 302, 303, 307, 308):
        raise ValueError("Redirect not allowed")
    
    if status == 200:
        return body
    
    raise ValueError("Non-200 status code")
