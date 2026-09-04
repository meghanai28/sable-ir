import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError("Invalid scheme")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Empty host")
    
    port = parsed.port
    if scheme == "http":
        if port is not None and port != 80:
            raise ValueError("Non-default port for HTTP")
        expected_port = 80
    else:
        if port is not None and port != 443:
            raise ValueError("Non-default port for HTTPS")
        expected_port = 443
    
    if port is None:
        port = expected_port
    
    ips = resolve_host(hostname)
    
    for ip_str in ips:
        ip = ipaddress.ip_address(ip_str)
        
        if ip.is_loopback:
            raise ValueError("Non-public IP: loopback")
        if ip.is_link_local:
            raise ValueError("Non-public IP: link-local")
        if ip.is_private:
            raise ValueError("Non-public IP: private")
        if ip.is_reserved:
            raise ValueError("Non-public IP: reserved")
        if ip.is_multicast:
            raise ValueError("Non-public IP: multicast")
        if ip.is_unspecified:
            raise ValueError("Non-public IP: unspecified")
        
        if isinstance(ip, ipaddress.IPv6Address):
            if ip.ipv4_mapped is not None:
                mapped = ipaddress.IPv4Address(ip.ipv4_mapped)
                if mapped.is_loopback or mapped.is_link_local or mapped.is_private or mapped.is_reserved or mapped.is_multicast:
                    raise ValueError("Non-public IP: IPv4-mapped non-public")
            if ip.ipv4_mapped is None:
                pass
        
        if ip_str.startswith("192.0.2.") or ip_str.startswith("198.51.100.") or ip_str.startswith("203.0.113."):
            raise ValueError("Non-public IP: documentation")
        if ip_str == "255.255.255.255":
            raise ValueError("Non-public IP: limited broadcast")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not followed")
    
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body
