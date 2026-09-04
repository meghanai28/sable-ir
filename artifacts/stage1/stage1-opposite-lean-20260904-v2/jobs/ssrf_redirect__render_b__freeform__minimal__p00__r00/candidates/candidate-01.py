import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname
    port = parsed.port
    
    if hostname is None:
        raise ValueError("Invalid URL: no hostname")
    
    if scheme == "http":
        if port is None:
            port = 80
        if port != 80:
            raise ValueError("Invalid port for http")
    elif scheme == "https":
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
    
    raise ValueError(f"Unexpected status: {status}")

def _is_public_ip(ip):
    try:
        parts = ip.split(".")
        if len(parts) == 4:
            a, b, c, d = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
            if not all(0 <= x <= 255 for x in (a, b, c, d)):
                return False
            
            # 0.0.0.0/8
            if a == 0:
                return False
            # 10.0.0.0/8
            if a == 10:
                return False
            # 127.0.0.0/8
            if a == 127:
                return False
            # 169.254.0.0/16
            if a == 169 and b == 254:
                return False
            # 172.16.0.0/12
            if a == 172 and 16 <= b <= 31:
                return False
            # 192.0.0.0/24
            if a == 192 and b == 0 and c == 0:
                return False
            # 192.0.2.0/24
            if a == 192 and b == 0 and c == 2:
                return False
            # 192.88.99.0/24
            if a == 192 and b == 88 and c == 99:
                return False
            # 192.168.0.0/16
            if a == 192 and b == 168:
                return False
            # 198.18.0.0/15
            if a == 198 and 18 <= b <= 19:
                return False
            # 198.51.100.0/24
            if a == 198 and b == 51 and c == 100:
                return False
            # 203.0.113.0/24
            if a == 203 and b == 0 and c == 113:
                return False
            # 224.0.0.0/4
            if 224 <= a <= 239:
                return False
            # 240.0.0.0/4
            if 240 <= a <= 255:
                return False
            
            return True
        
        # IPv6
        if ":" in ip:
            if ip == "::1":
                return False
            if ip.startswith("fc") or ip.startswith("fd"):
                return False
            if ip.startswith("fe80:"):
                return False
            if ip == "::" or ip.startswith("::ffff:"):
                # Check IPv4-mapped address
                if ip.startswith("::ffff:"):
                    ipv4_part = ip[7:]
                    return _is_public_ip(ipv4_part)
                return False
            if ip.startswith("ff"):
                return False
            if ip.startswith("::") and not ip.startswith("::ffff:"):
                # Other loopback or special forms
                if all(c in "0123456789abcdefABCDEF:." for c in ip):
                    return True
            return True
        
        return False
    except (ValueError, IndexError):
        return False
