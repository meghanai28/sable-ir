import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    if parsed.scheme == 'http' and parsed.port is not None and parsed.port != 80:
        raise ValueError("Invalid port for HTTP")
    if parsed.scheme == 'https' and parsed.port is not None and parsed.port != 443:
        raise ValueError("Invalid port for HTTPS")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("No hostname")
    
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError("No IPs resolved")
    
    has_public_ip = False
    for ip_str in ips:
        try:
            ip = ipaddress.ip_address(ip_str)
            if not ip.is_private and not ip.is_loopback and not ip.is_reserved and not ip.is_multicast and not ip.is_link_local:
                has_public_ip = True
                break
        except ValueError:
            continue
    
    if not has_public_ip:
        raise ValueError("No public IP")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError(f"Unexpected status: {status}")
    
    return body
