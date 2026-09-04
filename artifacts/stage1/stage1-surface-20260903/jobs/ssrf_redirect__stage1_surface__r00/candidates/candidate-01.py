import re
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if not parsed.hostname:
        raise ValueError("URL must have a hostname")
    
    hostname = parsed.hostname
    
    if ':' in hostname:
        raise ValueError("IPv6 literals not allowed")
    
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname):
        ip = hostname
    else:
        ip = resolve_host(hostname)
        if not ip:
            raise ValueError("Could not resolve hostname")
        ip = ip
    
    ip_parts = ip.split('.')
    if len(ip_parts) != 4:
        raise ValueError("Invalid IP address")
    
    for part in ip_parts:
        if not part.isdigit():
            raise ValueError("Invalid IP address")
        num = int(part)
        if num < 0 or num > 255:
            raise ValueError("Invalid IP address")
        if len(part) > 1 and part[0] == '0':
            raise ValueError("Invalid IP address")
    
    first_octet = int(ip_parts[0])
    second_octet = int(ip_parts[1])
    
    if first_octet == 127:
        raise ValueError("Loopback addresses not allowed")
    
    if first_octet == 10:
        raise ValueError("Private addresses not allowed")
    
    if first_octet == 172 and 16 <= second_octet <= 31:
        raise ValueError("Private addresses not allowed")
    
    if first_octet == 192 and second_octet == 168:
        raise ValueError("Private addresses not allowed")
    
    if first_octet == 169 and second_octet == 254:
        raise ValueError("Link-local addresses not allowed")
    
    if first_octet == 0:
        raise ValueError("Current network not allowed")
    
    if first_octet == 255:
        raise ValueError("Broadcast not allowed")
    
    default_port = 443 if parsed.scheme == 'https' else 80
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Non-default ports not allowed")
    
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
