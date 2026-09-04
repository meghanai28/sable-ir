import ipaddress
import re
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
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
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Non-default port not allowed")
    
    port = parsed.port if parsed.port is not None else default_port
    
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
        if isinstance(addr, ipaddress.IPv6Address) and addr.is_site_local:
            raise ValueError("Non-public IP address")
        if addr.is_multicast:
            raise ValueError("Non-public IP address")
        if addr.is_reserved:
            raise ValueError("Non-public IP address")
        if addr.is_unspecified:
            raise ValueError("Non-public IP address")
        
        if isinstance(addr, ipaddress.IPv6Address):
            if (addr.ipv4_mapped is not None or 
                addr.sixtofour is not None or 
                addr.teredo is not None):
                pass
        
        if isinstance(addr, ipaddress.IPv4Address):
            if addr == ipaddress.IPv4Address('0.0.0.0'):
                raise ValueError("Non-public IP address")
            if addr == ipaddress.IPv4Address('255.255.255.255'):
                raise ValueError("Non-public IP address")
        
        if isinstance(addr, ipaddress.IPv6Address):
            if addr.ipv4_mapped is not None:
                mapped = addr.ipv4_mapped
                if mapped.is_loopback or mapped.is_link_local or mapped.is_private or mapped.is_multicast or mapped.is_reserved or mapped.is_unspecified:
                    raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if status in (301, 302, 303, 307, 308):
        raise ValueError("Redirect not allowed")
    
    if status == 200:
        return body
    
    raise ValueError(f"Unexpected status code: {status}")
