import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Disallowed URL: only http and https are supported")
    
    # Validate port (must be default or absent)
    default_port = 443 if parsed.scheme == 'https' else 80
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Disallowed URL: non-default port specified")
    
    # Validate hostname is present
    if not parsed.hostname:
        raise ValueError("Disallowed URL: no hostname")
    
    # Resolve host and validate destination is public (not private/local)
    ip_addresses = resolve_host(parsed.hostname)
    if not ip_addresses:
        raise ValueError("Disallowed URL: host could not be resolved")
    
    for ip in ip_addresses:
        # Check for private/local IP ranges
        ip_obj = None
        try:
            # Try IPv4
            parts = ip.split('.')
            if len(parts) == 4:
                for p in parts:
                    if not p.isdigit() or not 0 <= int(p) <= 255:
                        raise ValueError("Disallowed URL: invalid IP address")
                first_octet = int(parts[0])
                second_octet = int(parts[1])
                # 10.0.0.0/8
                if first_octet == 10:
                    raise ValueError("Disallowed URL: private IP address")
                # 172.16.0.0/12
                if first_octet == 172 and 16 <= second_octet <= 31:
                    raise ValueError("Disallowed URL: private IP address")
                # 192.168.0.0/16
                if first_octet == 192 and second_octet == 168:
                    raise ValueError("Disallowed URL: private IP address")
                # 127.0.0.0/8 (loopback)
                if first_octet == 127:
                    raise ValueError("Disallowed URL: loopback IP address")
                # 169.254.0.0/16 (link-local)
                if first_octet == 169 and second_octet == 254:
                    raise ValueError("Disallowed URL: link-local IP address")
                # 0.0.0.0/8
                if first_octet == 0:
                    raise ValueError("Disallowed URL: reserved IP address")
                # 224.0.0.0+ (multicast)
                if 224 <= first_octet <= 239:
                    raise ValueError("Disallowed URL: multicast IP address")
                # 240.0.0.0+ (reserved)
                if first_octet >= 240:
                    raise ValueError("Disallowed URL: reserved IP address")
        except ValueError as e:
            if "Disallowed URL" in str(e):
                raise
            # Try IPv6
            pass
        
        try:
            # IPv6 checks
            if ':' in ip:
                # Normalize and check for IPv6
                ip_lower = ip.lower()
                # Loopback
                if ip_lower == '::1' or ip_lower == '0:0:0:0:0:0:0:1':
                    raise ValueError("Disallowed URL: loopback IP address")
                # IPv4-mapped loopback
                if '::ffff:127.' in ip_lower or '::ffff:7f' in ip_lower:
                    raise ValueError("Disallowed URL: loopback IP address")
                # Link-local
                if ip_lower.startswith('fe80:'):
                    raise ValueError("Disallowed URL: link-local IP address")
                # Unique local (fc00::/7)
                if ip_lower.startswith('fc') or ip_lower.startswith('fd'):
                    raise ValueError("Disallowed URL: private IP address")
                # Multicast (ff00::/8)
                if ip_lower.startswith('ff'):
                    raise ValueError("Disallowed URL: multicast IP address")
                # Unspecified
                if ip_lower == '::' or ip_lower == '0:0:0:0:0:0:0:0':
                    raise ValueError("Disallowed URL: unspecified IP address")
        except ValueError as e:
            if "Disallowed URL" in str(e):
                raise
            pass
    
    # Reconstruct URL without credentials
    netloc = parsed.hostname
    if parsed.port is not None:
        netloc += ':' + str(parsed.port)
    
    safe_url = urllib.parse.urlunparse((
        parsed.scheme,
        netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        ''  # Drop fragment
    ))
    
    # Invoke transport
    status, headers, body = transport(safe_url)
    
    # Check for redirect (3xx status codes)
    if 300 <= status < 400:
        raise ValueError("Disallowed: redirect response rejected")
    
    # Return body for 200, raise for non-200
    if status == 200:
        if isinstance(body, bytes):
            return body.decode('utf-8', errors='replace')
        return str(body)
    
    raise ValueError(f"Disallowed: non-200 status code {status}")
