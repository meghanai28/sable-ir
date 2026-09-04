import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    if parsed.scheme == 'http' and parsed.port is not None and parsed.port != 80:
        raise ValueError("Invalid port")
    if parsed.scheme == 'https' and parsed.port is not None and parsed.port != 443:
        raise ValueError("Invalid port")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("No hostname")
    
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError("No IP addresses resolved")
    
    has_public = False
    for ip_str in ips:
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_global:
                has_public = True
                break
        except ValueError:
            continue
    
    if not has_public:
        raise ValueError("No public IP addresses")
    
    status, headers, body = transport(url)
    
    if status in (301, 302, 303, 307, 308):
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body
