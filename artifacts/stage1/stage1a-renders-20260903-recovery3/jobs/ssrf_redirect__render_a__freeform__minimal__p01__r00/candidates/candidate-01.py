import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if parsed.port is not None:
        default_port = 443 if parsed.scheme == 'https' else 80
        if parsed.port != default_port:
            raise ValueError("Non-default port not allowed")
    
    if not parsed.hostname:
        raise ValueError("URL must have a hostname")
    
    ips = resolve_host(parsed.hostname)
    if not ips:
        raise ValueError("No IP addresses resolved for hostname")
    
    has_public_ip = False
    for ip_str in ips:
        try:
            ip = ipaddress.ip_address(ip_str)
            if not ip.is_private and not ip.is_loopback and not ip.is_reserved and not ip.is_multicast and not ip.is_link_local and not ip.is_unspecified:
                has_public_ip = True
                break
        except ValueError:
            continue
    
    if not has_public_ip:
        raise ValueError("No public IP address found for hostname")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects are not allowed")
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
