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
        raise ValueError("Redirects not allowed")
    
    if status == 200:
        return body
    
    raise ValueError("Unexpected status code")

def _is_public_ip(ip):
    try:
        import ipaddress
        addr = ipaddress.ip_address(ip)
        return not (
            addr.is_private or
            addr.is_loopback or
            addr.is_link_local or
            addr.is_multicast or
            addr.is_reserved or
            addr.is_unspecified
        )
    except ValueError:
        return False
