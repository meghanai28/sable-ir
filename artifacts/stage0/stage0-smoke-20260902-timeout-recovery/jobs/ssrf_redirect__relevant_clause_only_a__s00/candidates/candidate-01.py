import ipaddress

def fetch_text(url, transport, resolve_host):
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if parsed.port is not None:
        if parsed.scheme == 'http' and parsed.port != 80:
            raise ValueError("HTTP must use default port 80")
        if parsed.scheme == 'https' and parsed.port != 443:
            raise ValueError("HTTPS must use default port 443")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("URL must have a hostname")
    
    if hostname.startswith('[') and hostname.endswith(']'):
        host_to_resolve = hostname[1:-1]
    else:
        host_to_resolve = hostname
    
    try:
        ip = ipaddress.ip_address(host_to_resolve)
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast or ip.is_link_local:
            raise ValueError("Private IP addresses are not allowed")
    except ValueError:
        ips = resolve_host(host_to_resolve)
        if not ips:
            raise ValueError("Could not resolve hostname")
        for resolved_ip in ips:
            ip = ipaddress.ip_address(resolved_ip)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast or ip.is_link_local:
                raise ValueError("Private IP addresses are not allowed")
    
    status, headers, body = transport(url)
    
    if status in (301, 302, 303, 307, 308):
        raise ValueError("Redirects are not followed")
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
