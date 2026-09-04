import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    # Validate port (must be default or unspecified)
    if parsed.scheme == 'http':
        default_port = 80
    else:
        default_port = 443
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Disallowed non-default port")
    
    # Validate hostname exists
    if not parsed.hostname:
        raise ValueError("Missing hostname")
    
    # Check destination is public using resolve_host
    try:
        ips = resolve_host(parsed.hostname)
    except Exception:
        raise ValueError("Failed to resolve host")
    
    if not ips:
        raise ValueError("Host resolved to no addresses")
    
    for ip in ips:
        # Check for private/loopback/link-local addresses
        if ip.startswith('127.') or ip == '::1' or ip.startswith('0:0:0:0:0:0:0:1'):
            raise ValueError("Disallowed private destination")
        if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
            # Check 172.16.0.0/12
            if ip.startswith('172.'):
                try:
                    second_octet = int(ip.split('.')[1])
                    if 16 <= second_octet <= 31:
                        raise ValueError("Disallowed private destination")
                except (ValueError, IndexError):
                    pass
            else:
                raise ValueError("Disallowed private destination")
        if ip.startswith('169.254.'):
            raise ValueError("Disallowed link-local destination")
        if ip.startswith('fc00:') or ip.startswith('fd00:'):
            raise ValueError("Disallowed private destination")
        if ip == '0.0.0.0':
            raise ValueError("Disallowed destination")
    
    # Invoke transport
    status, headers, body = transport(url)
    
    # Reject any redirect without following
    if status in (301, 302, 303, 307, 308):
        raise ValueError("Redirects not followed")
    
    # Return body on 200
    if status == 200:
        if isinstance(body, bytes):
            return body.decode('utf-8')
        return str(body)
    
    raise ValueError("Non-200 status")
