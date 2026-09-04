import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname
    port = parsed.port
    
    if hostname is None:
        raise ValueError("Invalid URL: no hostname")
    
    if scheme == 'http':
        if port is None:
            port = 80
        if port != 80:
            raise ValueError("Invalid port for http")
    elif scheme == 'https':
        if port is None:
            port = 443
        if port != 443:
            raise ValueError("Invalid port for https")
    else:
        raise ValueError("Invalid scheme")
    
    ip_addresses = resolve_host(hostname)
    for ip in ip_addresses:
        if not _is_public_ip(ip):
            raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status == 200:
        return body
    
    raise ValueError("Unexpected status code")

def _is_public_ip(ip):
    try:
        parts = ip.split('.')
        if len(parts) == 4:
            a, b, c, d = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
            if not all(0 <= x <= 255 for x in (a, b, c, d)):
                return False
            
            if a == 0:
                return False
            if a == 10:
                return False
            if a == 100 and 64 <= b <= 127:
                return False
            if a == 127:
                return False
            if a == 169 and b == 254:
                return False
            if a == 172 and 16 <= b <= 31:
                return False
            if a == 192 and b == 0 and c == 0:
                return False
            if a == 192 and b == 0 and c == 2:
                return False
            if a == 192 and b == 88 and c == 99:
                return False
            if a == 192 and b == 168:
                return False
            if a == 198 and b == 18:
                return False
            if a == 198 and b == 51 and c == 100:
                return False
            if a == 203 and b == 0 and c == 113:
                return False
            if 224 <= a <= 239:
                return False
            if 240 <= a <= 255:
                return False
            
            return True
        
        parts = ip.split(':')
        if len(parts) > 2:
            if '::' in ip:
                expanded = _expand_ipv6(ip)
                if expanded is None:
                    return False
                parts = expanded.split(':')
            
            if len(parts) != 8:
                return False
            
            for part in parts:
                if not part:
                    return False
                try:
                    val = int(part, 16)
                    if not 0 <= val <= 65535:
                        return False
                except ValueError:
                    return False
            
            first = int(parts[0], 16)
            if (first & 0xFE00) == 0xFC00:
                return False
            if (first & 0xFFC0) == 0xFE80:
                return False
            if (first & 0xFF00) == 0xFF00:
                return False
            if first == 0 and all(int(p, 16) == 0 for p in parts):
                return False
            if first == 0 and int(parts[1], 16) == 0 and int(parts[2], 16) == 0 and int(parts[3], 16) == 0 and int(parts[4], 16) == 0 and int(parts[5], 16) == 0xFFFF:
                mapped = '.'.join(str(int(parts[i], 16)) for i in (6, 7))
                mapped_parts = mapped.split('.')
                a, b = int(mapped_parts[0]), int(mapped_parts[1])
                if a == 127:
                    return False
                if a == 10:
                    return False
                if a == 172 and 16 <= b <= 31:
                    return False
                if a == 192 and b == 168:
                    return False
            
            return True
        
        return False
    except (ValueError, IndexError):
        return False

def _expand_ipv6(ip):
    if ip.count('::') > 1:
        return None
    if '::' in ip:
        left, right = ip.split('::', 1)
        left_parts = left.split(':') if left else []
        right_parts = right.split(':') if right else []
        missing = 8 - len(left_parts) - len(right_parts)
        if missing < 0:
            return None
        parts = left_parts + ['0'] * missing + right_parts
        return ':'.join(parts)
    return ip
