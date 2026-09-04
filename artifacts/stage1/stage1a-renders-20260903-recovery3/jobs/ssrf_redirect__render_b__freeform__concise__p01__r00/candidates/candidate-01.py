import re
import urllib.parse

def fetch_text(url, transport, resolve_host):
    def is_public_ip(ip):
        # IPv4
        ipv4_match = re.match(r'^(\d+)\.(\d+)\.(\d+)\.(\d+)$', ip)
        if ipv4_match:
            a, b, c, d = map(int, ipv4_match.groups())
            if not (0 <= a <= 255 and 0 <= b <= 255 and 0 <= c <= 255 and 0 <= d <= 255):
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
        if ip.startswith('[') and ip.endswith(']'):
            ip = ip[1:-1]
        
        # Check for IPv6
        if ':' in ip:
            # Normalize and validate IPv6
            try:
                # Basic validation
                if '::' in ip:
                    parts = ip.split('::')
                    if len(parts) > 2:
                        return False
                    left = parts[0].split(':') if parts[0] else []
                    right = parts[1].split(':') if parts[1] else []
                    if len(left) + len(right) > 7:
                        return False
                    total = left + ['0'] * (8 - len(left) - len(right)) + right
                else:
                    total = ip.split(':')
                    if len(total) != 8:
                        return False
                
                # Check for IPv4-mapped
                if '.' in total[-1]:
                    # IPv4-mapped or IPv4-compatible
                    ipv4_part = total[-1]
                    if not is_public_ip(ipv4_part):
                        return False
                    total = total[:-1] + ['0', '0']
                
                # Validate hex parts
                for part in total:
                    if len(part) > 4:
                        return False
                    int(part, 16)  # Validate hex
                
                # Check for loopback ::1
                if ip == '::1' or ip == '0:0:0:0:0:0:0:1':
                    return False
                
                # Check for unspecified ::/128
                if ip == '::' or all(p == '0' for p in total):
                    return False
                
                # Check for fc00::/7 (unique local)
                first = int(total[0], 16)
                if (first & 0xfe00) == 0xfc00:
                    return False
                
                # Check for fe80::/10 (link-local)
                if (first & 0xffc0) == 0xfe80:
                    return False
                
                # Check for multicast ff00::/8
                if (first & 0xff00) == 0xff00:
                    return False
                
                # Check for ::ffff:0:0/96 (IPv4-mapped, already handled above for IPv4 part)
                
                return True
            except ValueError:
                return False
        
        return False
    
    def validate_url(parsed):
        # Scheme check
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS schemes are allowed")
        
        # Port check
        port = parsed.port
        if port is None:
            port = 80 if parsed.scheme == 'http' else 443
        
        if parsed.scheme == 'http' and port != 80:
            raise ValueError("HTTP must use default port 80")
        if parsed.scheme == 'https' and port != 443:
            raise ValueError("HTTPS must use default port 443")
        
        # Userinfo check - reject any credentials
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Userinfo in URL is not allowed")
        
        # Hostname check
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Hostname is required")
        
        # Resolve and validate IP addresses
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("Could not resolve hostname")
        
        for ip in ips:
            if not is_public_ip(ip):
                raise ValueError("Resolved IP address is not public: " + ip)
        
        # Rebuild sanitized URL without userinfo
        sanitized = urllib.parse.urlunparse((
            parsed.scheme,
            hostname + ((':' + str(port)) if ((parsed.scheme == 'http' and port != 80) or (parsed.scheme == 'https' and port != 443)) else ''),
            parsed.path or '/',
            parsed.params,
            parsed.query,
            ''  # Drop fragment
        ))
        
        return sanitized
    
    def resolve_location(base, location):
        return urllib.parse.urljoin(base, location)
    
    current_url = url
    redirect_count = 0
    max_redirects = 5
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        sanitized = validate_url(parsed)
        
        status, headers, body = transport(sanitized)
        
        if status == 200:
            # Return body as text
            if isinstance(body, bytes):
                return body.decode('utf-8', errors='replace')
            return str(body)
        
        if 300 <= status < 400:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
            
            location = None
            for key, value in headers.items() if isinstance(headers, dict) else headers:
                if key.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Redirect without Location header")
            
            current_url = resolve_location(current_url, location)
            continue
        
        raise ValueError(f"Unsupported HTTP status: {status}")
