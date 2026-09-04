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
        raise ValueError("Disallowed scheme")
    
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
    
    for addr in ip_addresses:
        try:
            ip = ipaddress.ip_address(addr)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
                raise ValueError("Non-public IP address")
        except ValueError:
            raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not followed")
    
    if status == 200:
        return body
    
    raise ValueError("Non-200 status")
