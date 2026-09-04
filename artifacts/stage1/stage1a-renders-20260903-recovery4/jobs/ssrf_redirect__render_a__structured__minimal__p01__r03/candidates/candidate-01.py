import ipaddress
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    
    scheme = parsed.scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    default_port = 443 if scheme == 'https' else 80
    port = parsed.port if parsed.port is not None else default_port
    if port != default_port:
        raise ValueError("Disallowed port")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    if hostname.startswith('[') and hostname.endswith(']'):
        host_for_resolve = hostname[1:-1]
    else:
        host_for_resolve = hostname
    
    try:
        ipaddress.ip_address(host_for_resolve)
        is_ip_literal = True
    except ValueError:
        is_ip_literal = False
    
    if is_ip_literal:
        ip_str = host_for_resolve
    else:
        ip_addresses = resolve_host(host_for_resolve)
        if not ip_addresses:
            raise ValueError("Non-public host")
        ip_str = ip_addresses[0]
    
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        raise ValueError("Non-public host")
    
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_reserved or addr.is_unspecified:
        raise ValueError("Non-public host")
    
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        mapped = addr.ipv4_mapped
        if mapped.is_private or mapped.is_loopback or mapped.is_link_local or mapped.is_multicast or mapped.is_reserved or mapped.is_unspecified:
            raise ValueError("Non-public host")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not followed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    if isinstance(body, bytes):
        return body.decode('utf-8')
    
    return str(body)
