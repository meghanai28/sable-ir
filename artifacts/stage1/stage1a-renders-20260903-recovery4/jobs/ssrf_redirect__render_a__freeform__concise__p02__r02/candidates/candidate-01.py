import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme == 'http':
        default_port = 80
    elif scheme == 'https':
        default_port = 443
    else:
        raise ValueError("Invalid scheme")
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Non-default port")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("No hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Resolution failed")
    
    if not ip_addresses:
        raise ValueError("Resolution failed")
    
    for addr_str in ip_addresses:
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            raise ValueError("Invalid IP address")
        
        if addr.is_private:
            raise ValueError("Non-public IP address")
        if addr.is_loopback:
            raise ValueError("Non-public IP address")
        if addr.is_link_local:
            raise ValueError("Non-public IP address")
        if addr.is_multicast:
            raise ValueError("Non-public IP address")
        if addr.is_reserved:
            raise ValueError("Non-public IP address")
        if addr.is_unspecified:
            raise ValueError("Non-public IP address")
        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
            mapped = addr.ipv4_mapped
            if mapped.is_private or mapped.is_loopback or mapped.is_link_local or mapped.is_multicast or mapped.is_reserved or mapped.is_unspecified:
                raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not followed")
    
    if status == 200:
        return body
    
    raise ValueError("Unexpected status")
