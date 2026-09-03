import re
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if not parsed.hostname:
        raise ValueError("URL must have a hostname")
    
    if parsed.port is not None and parsed.port != (443 if parsed.scheme == 'https' else 80):
        raise ValueError("Non-default ports are not allowed")
    
    if '@' in parsed.netloc:
        raise ValueError("Userinfo in URL is not allowed")
    
    hostname = parsed.hostname.lower()
    
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname):
        ip = hostname
    elif ':' in hostname:
        ip = hostname
    else:
        resolved_ips = resolve_host(hostname)
        if not resolved_ips:
            raise ValueError("Could not resolve hostname")
        ip = resolved_ips[0]
    
    if ip.startswith('127.') or ip.startswith('0.') or ip == '::1' or ip == '0:0:0:0:0:0:0:1':
        raise ValueError("Loopback addresses are not allowed")
    
    if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
        if ip.startswith('172.'):
            second_octet = int(ip.split('.')[1])
            if 16 <= second_octet <= 31:
                raise ValueError("Private addresses are not allowed")
        else:
            raise ValueError("Private addresses are not allowed")
    
    if ip.startswith('169.254.'):
        raise ValueError("Link-local addresses are not allowed")
    
    if ip.startswith('fc00:') or ip.startswith('fd00:'):
        raise ValueError("Unique local addresses are not allowed")
    
    if ip.startswith('fe80:'):
        raise ValueError("Link-local addresses are not allowed")
    
    status, headers, body = transport(url)
    
    if status in (301, 302, 303, 307, 308):
        raise ValueError("Redirects are not followed")
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
