import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    
    if scheme not in ('http', 'https'):
        raise ValueError("Only http and https schemes are allowed")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("URL must contain a hostname")
    
    port = parsed.port
    if port is None:
        port = 80 if scheme == 'http' else 443
    
    default_port = 80 if scheme == 'http' else 443
    if port != default_port:
        raise ValueError("Only default ports are allowed")
    
    resolved_ips = resolve_host(hostname)
    if not resolved_ips:
        raise ValueError("Hostname could not be resolved")
    
    for ip_str in resolved_ips:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError("Invalid IP address returned by resolver")
        
        if ip.is_private:
            raise ValueError("Private IP addresses are not allowed")
        if ip.is_loopback:
            raise ValueError("Loopback IP addresses are not allowed")
        if ip.is_reserved:
            raise ValueError("Reserved IP addresses are not allowed")
        if ip.is_multicast:
            raise ValueError("Multicast IP addresses are not allowed")
        if ip.is_link_local:
            raise ValueError("Link-local IP addresses are not allowed")
        if ip.version == 4 and ip.is_unspecified:
            raise ValueError("Unspecified IP addresses are not allowed")
        if ip.version == 6 and ip == ipaddress.IPv6Address('::'):
            raise ValueError("Unspecified IP addresses are not allowed")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects are not followed")
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
