import ipaddress
import re
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    default_port = 80 if scheme == 'http' else 443
    
    host = parsed.hostname
    if host is None:
        raise ValueError("Missing host")
    
    if '@' in parsed.netloc:
        netloc = parsed.netloc
        if netloc.startswith('@'):
            host_part = netloc[1:]
        else:
            host_part = netloc.split('@', 1)[1]
    else:
        host_part = parsed.netloc
    
    if ':' in host_part:
        if host_part.startswith('['):
            bracket_end = host_part.find(']')
            if bracket_end != -1:
                after_bracket = host_part[bracket_end + 1:]
                if after_bracket.startswith(':'):
                    explicit_port_str = after_bracket[1:]
                    if explicit_port_str:
                        explicit_port = int(explicit_port_str)
                        if explicit_port != default_port:
                            raise ValueError("Non-default explicit port")
        else:
            colon_parts = host_part.rsplit(':', 1)
            if len(colon_parts) == 2 and colon_parts[1].isdigit():
                explicit_port = int(colon_parts[1])
                if explicit_port != default_port:
                    raise ValueError("Non-default explicit port")
    
    host_str = host
    
    try:
        ip_addr = ipaddress.ip_address(host_str)
        resolved_addresses = [str(ip_addr)]
    except ValueError:
        resolved_addresses = resolve_host(host_str)
    
    if not resolved_addresses:
        raise ValueError("No resolved addresses")
    
    for addr in resolved_addresses:
        ip = ipaddress.ip_address(addr)
        if ip.is_loopback:
            raise ValueError("Non-public IP address")
        if ip.is_link_local:
            raise ValueError("Non-public IP address")
        if ip.is_private:
            raise ValueError("Non-public IP address")
        if ip.is_multicast:
            raise ValueError("Non-public IP address")
        if ip.is_reserved:
            raise ValueError("Non-public IP address")
        if ip.is_unspecified:
            raise ValueError("Non-public IP address")
        if hasattr(ipaddress, 'IPv6Address') and isinstance(ip, ipaddress.IPv6Address):
            if ip.ipv4_mapped is not None:
                ipv4 = ip.ipv4_mapped
                if ipv4.is_loopback or ipv4.is_link_local or ipv4.is_private or ipv4.is_multicast or ipv4.is_reserved or ipv4.is_unspecified:
                    raise ValueError("Non-public IP address")
            if ip.sixtofour is not None:
                ipv4 = ip.sixtofour
                if ipv4.is_loopback or ipv4.is_link_local or ipv4.is_private or ipv4.is_multicast or ipv4.is_reserved or ipv4.is_unspecified:
                    raise ValueError("Non-public IP address")
            if ip.teredo is not None:
                ipv4 = ip.teredo[1]
                if ipv4.is_loopback or ipv4.is_link_local or ipv4.is_private or ipv4.is_multicast or ipv4.is_reserved or ipv4.is_unspecified:
                    raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not followed")
    
    if status != 200:
        raise ValueError("Non-200 status code")
    
    if isinstance(body, bytes):
        return body.decode('utf-8')
    return str(body)
