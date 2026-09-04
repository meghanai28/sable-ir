import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    if parsed.scheme == 'http' and parsed.port is not None and parsed.port != 80:
        raise ValueError("Disallowed port")
    if parsed.scheme == 'https' and parsed.port is not None and parsed.port != 443:
        raise ValueError("Disallowed port")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    if hostname.startswith('[') and hostname.endswith(']'):
        host_for_resolve = hostname[1:-1]
    else:
        host_for_resolve = hostname
    
    try:
        ips = resolve_host(host_for_resolve)
    except Exception:
        raise ValueError("Failed to resolve host")
    
    if not ips:
        raise ValueError("No IP addresses resolved")
    
    for ip in ips:
        if ip.startswith('127.') or ip == '0.0.0.0':
            raise ValueError("Non-public destination")
        if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
            if ip.startswith('172.'):
                try:
                    second_octet = int(ip.split('.')[1])
                    if 16 <= second_octet <= 31:
                        raise ValueError("Non-public destination")
                except (ValueError, IndexError):
                    pass
            else:
                raise ValueError("Non-public destination")
        if ':' in ip:
            if ip == '::1' or ip == '::' or ip.startswith('fc') or ip.startswith('fd') or ip.startswith('fe80:'):
                raise ValueError("Non-public destination")
            if ip.startswith('::ffff:'):
                ipv4_part = ip[7:]
                if ipv4_part.startswith('127.') or ipv4_part == '0.0.0.0':
                    raise ValueError("Non-public destination")
                if ipv4_part.startswith('10.') or ipv4_part.startswith('192.168.') or ipv4_part.startswith('172.'):
                    if ipv4_part.startswith('172.'):
                        try:
                            second_octet = int(ipv4_part.split('.')[1])
                            if 16 <= second_octet <= 31:
                                raise ValueError("Non-public destination")
                        except (ValueError, IndexError):
                            pass
                    else:
                        raise ValueError("Non-public destination")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    if status != 200:
        raise ValueError("Disallowed status")
    
    return body
