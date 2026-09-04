import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
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
    
    addresses = resolve_host(hostname)
    
    if not addresses:
        raise ValueError
    
    for addr in addresses:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            raise ValueError
        
        if ip.is_private:
            raise ValueError
        if ip.is_loopback:
            raise ValueError
        if ip.is_link_local:
            raise ValueError
        if ip.is_multicast:
            raise ValueError
        if ip.is_reserved:
            raise ValueError
        if ip.is_unspecified:
            raise ValueError
        
        if isinstance(ip, ipaddress.IPv6Address):
            if ip.ipv4_mapped is not None:
                ipv4 = ip.ipv4_mapped
                if ipv4.is_private or ipv4.is_loopback or ipv4.is_link_local or ipv4.is_multicast or ipv4.is_reserved or ipv4.is_unspecified:
                    raise ValueError
            
            if ip.is_site_local:
                raise ValueError
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError
    
    if status != 200:
        raise ValueError
    
    return body
