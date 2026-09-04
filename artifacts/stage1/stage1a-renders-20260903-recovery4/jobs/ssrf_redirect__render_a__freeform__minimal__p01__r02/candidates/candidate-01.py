import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if parsed.port is None:
        expected_port = 443 if parsed.scheme == 'https' else 80
    else:
        expected_port = parsed.port
    
    if parsed.scheme == 'http' and expected_port != 80:
        raise ValueError("HTTP must use default port 80")
    if parsed.scheme == 'https' and expected_port != 443:
        raise ValueError("HTTPS must use default port 443")
    
    if not parsed.hostname:
        raise ValueError("URL must have a hostname")
    
    ip_texts = resolve_host(parsed.hostname)
    
    if not ip_texts:
        raise ValueError("No IP addresses resolved for hostname")
    
    has_public_ip = False
    for ip_text in ip_texts:
        try:
            addr = ipaddress.ip_address(ip_text)
            if not addr.is_private and not addr.is_loopback and not addr.is_link_local and not addr.is_multicast and not addr.is_reserved and not addr.is_unspecified:
                has_public_ip = True
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
