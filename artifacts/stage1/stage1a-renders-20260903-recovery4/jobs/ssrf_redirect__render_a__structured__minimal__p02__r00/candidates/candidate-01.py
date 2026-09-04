import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname
    port = parsed.port
    
    if scheme == 'http':
        default_port = 80
    elif scheme == 'https':
        default_port = 443
    else:
        raise ValueError("Invalid scheme")
    
    if port is None:
        port = default_port
    
    if port != default_port:
        raise ValueError("Non-default port")
    
    if hostname is None:
        raise ValueError("Missing hostname")
    
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError("No IPs resolved")
    
    for ip_str in ips:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise ValueError("Non-public IP")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not followed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body
