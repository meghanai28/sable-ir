import re
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    port = parsed.port
    if port is None:
        port = 80 if scheme == 'http' else 443
    
    if (scheme == 'http' and port != 80) or (scheme == 'https' and port != 443):
        raise ValueError("Disallowed port")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    if hostname.startswith('[') and hostname.endswith(']'):
        ip_str = hostname[1:-1]
    else:
        ip_str = hostname
    
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve host")
    
    if not resolved_ips:
        raise ValueError("No resolved IPs")
    
    for ip in resolved_ips:
        if _is_private_ip(ip):
            raise ValueError("Non-public host")
    
    status, headers, body = transport(url)
    
    if status >= 300 and status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError(f"Unexpected status: {status}")
    
    return body


def _is_private_ip(ip_str):
    ip_str = ip_str.strip()
    
    if ip_str.lower().startswith('0x') or ip_str.lower().startswith('0X'):
        try:
            ip_str = str(int(ip_str, 16))
        except ValueError:
            pass
    
    if ip_str.startswith('0') and len(ip_str) > 1 and ip_str[1:].isdigit():
        try:
            ip_str = str(int(ip_str, 8))
        except ValueError:
            pass
    
    if ip_str.startswith('[') and ip_str.endswith(']'):
        ip_str = ip_str[1:-1]
    
    if ':' in ip_str:
        return _is_private_ipv6(ip_str)
    else:
        return _is_private_ipv4(ip_str)


def _is_private_ipv4(ip_str):
    parts = ip_str.split('.')
    if len(parts) != 4:
        return True
    
    try:
        octets = [int(p) for p in parts]
    except ValueError:
        return True
    
    for o in octets:
        if o < 0 or o > 255:
            return True
    
    if octets[0] == 0:
        return True
    
    if octets[0] == 10:
        return True
    
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return True
    
    if octets[0] == 192 and octets[1] == 168:
        return True
    
    if octets[0] == 127:
        return True
    
    if octets[0] == 169 and octets[1] == 254:
        return True
    
    if octets[0] >= 224:
        return True
    
    return False


def _is_private_ipv6(ip_str):
    ip_str = ip_str.lower()
    
    if ip_str == '::1' or ip_str == '0:0:0:0:0:0:0:1':
        return True
    
    if ip_str.startswith('fe80:'):
        return True
    
    if ip_str.startswith('fc') or ip_str.startswith('fd'):
        return True
    
    if ip_str.startswith('ff'):
        return True
    
    if ip_str == '::' or ip_str == '0:0:0:0:0:0:0:0':
        return True
    
    parts = ip_str.split(':')
    
    if '::' in ip_str:
        expanded = _expand_ipv6(ip_str)
        if expanded is None:
            return True
        parts = expanded.split(':')
    
    if len(parts) != 8:
        return True
    
    try:
        for p in parts:
            if len(p) > 4:
                return True
            val = int(p, 16)
            if val < 0 or val > 65535:
                return True
    except ValueError:
        return True
    
    return False


def _expand_ipv6(ip_str):
    if '::' not in ip_str:
        return ip_str
    
    if ip_str.count('::') > 1:
        return None
    
    left, right = ip_str.split('::')
    
    left_parts = [p for p in left.split(':') if p] if left else []
    right_parts = [p for p in right.split(':') if p] if right else []
    
    missing = 8 - len(left_parts) - len(right_parts)
    if missing < 0:
        return None
    
    middle = ['0'] * missing
    all_parts = left_parts + middle + right_parts
    
    if len(all_parts) != 8:
        return None
    
    return ':'.join(all_parts)
