import re
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if not parsed.hostname:
        raise ValueError("URL must have a hostname")
    
    default_port = 443 if parsed.scheme == 'https' else 80
    port = parsed.port if parsed.port is not None else default_port
    
    if port != default_port:
        raise ValueError("Only default ports are allowed")
    
    hostname = parsed.hostname
    
    ip_addresses = resolve_host(hostname)
    
    for ip in ip_addresses:
        if _is_private_ip(ip):
            raise ValueError("Private IP addresses are not allowed")
    
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body

def _is_private_ip(ip):
    ip = ip.strip()
    
    if ip.startswith('::ffff:'):
        ip = ip[7:]
    
    if '.' in ip:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        try:
            octets = [int(p) for p in parts]
        except ValueError:
            return False
        
        if not all(0 <= o <= 255 for o in octets):
            return False
        
        if octets[0] == 10:
            return True
        if octets[0] == 172 and 16 <= octets[1] <= 31:
            return True
        if octets[0] == 192 and octets[1] == 168:
            return True
        if octets[0] == 127:
            return True
        if octets[0] == 0:
            return True
        if octets[0] == 169 and octets[1] == 254:
            return True
        
        return False
    
    if ':' in ip:
        if ip == '::1':
            return True
        if ip.startswith('fc') or ip.startswith('fd'):
            return True
        if ip.startswith('fe80:') or ip.startswith('FE80:'):
            return True
        if ip == '::' or ip == '0:0:0:0:0:0:0:0':
            return True
        
        return False
    
    return False
