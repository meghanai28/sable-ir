import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    host = parsed.hostname
    if host is None or host == '':
        raise ValueError("Empty host")
    
    default_port = 80 if scheme == 'http' else 443
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Non-default port")
    
    addresses = []
    try:
        ip_addr = ipaddress.ip_address(host)
        addresses.append(str(ip_addr))
    except ValueError:
        resolved = resolve_host(host)
        if not resolved:
            raise ValueError("Host resolution failed")
        addresses = resolved
    
    for addr_str in addresses:
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            raise ValueError("Invalid IP address")
        
        if isinstance(addr, ipaddress.IPv4Address):
            if (
                addr.is_loopback
                or addr.is_private
                or addr.is_link_local
                or addr.is_reserved
                or addr.is_multicast
                or addr.is_unspecified
            ):
                raise ValueError("Non-public IP address")
        elif isinstance(addr, ipaddress.IPv6Address):
            if (
                addr.is_loopback
                or addr.is_link_local
                or addr.is_private
                or addr.is_multicast
                or addr.is_unspecified
            ):
                raise ValueError("Non-public IP address")
            if addr.ipv4_mapped is not None:
                mapped = addr.ipv4_mapped
                if (
                    mapped.is_loopback
                    or mapped.is_private
                    or mapped.is_link_local
                    or mapped.is_reserved
                    or mapped.is_multicast
                    or mapped.is_unspecified
                ):
                    raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body
