import re
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    default_port = 80 if parsed.scheme == 'http' else 443
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Disallowed port")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Non-public host")
    
    for ip in ip_addresses:
        if _is_private_ip(ip):
            raise ValueError("Non-public host")
    
    status, headers, body = transport(url)
    
    if status in (301, 302, 303, 307, 308):
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Disallowed request")
    
    return body.decode('utf-8') if isinstance(body, bytes) else str(body)

def _is_private_ip(ip):
    ip = ip.strip()
    
    if ip.startswith('127.'):
        return True
    
    if ip.startswith('10.'):
        return True
    
    if ip.startswith('172.'):
        parts = ip.split('.')
        if len(parts) >= 2:
            second = int(parts[1])
            if 16 <= second <= 31:
                return True
    
    if ip.startswith('192.168.'):
        return True
    
    if ip == '0.0.0.0':
        return True
    
    if ':' in ip:
        if ip == '::1':
            return True
        if ip.startswith('fc') or ip.startswith('fd'):
            return True
        if ip.startswith('fe80:'):
            return True
    
    return False
