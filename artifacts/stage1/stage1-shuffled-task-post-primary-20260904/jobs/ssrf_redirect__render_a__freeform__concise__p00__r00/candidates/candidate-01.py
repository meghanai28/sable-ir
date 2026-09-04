import os
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS are allowed")
    
    if parsed.port is not None and parsed.port != (443 if parsed.scheme == 'https' else 80):
        raise ValueError("Non-default port not allowed")
    
    if not parsed.hostname:
        raise ValueError("URL must have a hostname")
    
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must not contain credentials")
    
    hostname = parsed.hostname
    ips = resolve_host(hostname)
    
    if not ips:
        raise ValueError("Could not resolve hostname")
    
    for ip in ips:
        if ip.startswith('127.') or ip == '0.0.0.0' or ip == '::1' or ip == '::' or ip.startswith('0:') or ip.startswith('fc') or ip.startswith('fd') or ip.startswith('fe80:') or ip.startswith('::ffff:127.'):
            raise ValueError("Private or loopback IP not allowed")
    
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
