import ipaddress
import urllib.parse

def _validate_url(url):
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        raise ValueError("Invalid URL")
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    default_port = 443 if parsed.scheme == 'https' else 80
    port = parsed.port
    if port is None:
        port = default_port
    if port != default_port:
        raise ValueError("Invalid port")
    
    if not parsed.hostname:
        raise ValueError("Missing hostname")
    
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials not allowed")
    
    hostname = parsed.hostname.lower()
    
    if hostname.startswith('[') and hostname.endswith(']'):
        raise ValueError("IPv6 literal not allowed in URL")
    
    try:
        ipaddress.ip_address(hostname)
        raise ValueError("IP literal not allowed in URL")
    except ValueError:
        pass
    
    return parsed, hostname, port

def _validate_ip(ip_str, hostname):
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        raise ValueError("Invalid IP address")
    
    if ip.is_private:
        raise ValueError("Private IP not allowed")
    if ip.is_loopback:
        raise ValueError("Loopback IP not allowed")
    if ip.is_link_local:
        raise ValueError("Link local IP not allowed")
    if ip.is_multicast:
        raise ValueError("Multicast IP not allowed")
    if ip.is_reserved:
        raise ValueError("Reserved IP not allowed")
    if ip.is_unspecified:
        raise ValueError("Unspecified IP not allowed")
    
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            mapped = ipaddress.IPv4Address(ip.ipv4_mapped)
            if mapped.is_private or mapped.is_loopback or mapped.is_link_local or mapped.is_multicast or mapped.is_reserved or mapped.is_unspecified:
                raise ValueError("Mapped private IP not allowed")
    
    return ip

def _resolve_and_validate(parsed, resolve_host):
    hostname = parsed.hostname.lower()
    
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError("DNS resolution failed")
    
    for ip_str in ips:
        _validate_ip(ip_str, hostname)
    
    return parsed

def _resolve_location(location, current_url):
    try:
        resolved = urllib.parse.urljoin(current_url, location)
    except Exception:
        raise ValueError("Invalid Location header")
    return resolved

def fetch_text(url, transport, resolve_host):
    parsed, hostname, port = _validate_url(url)
    _resolve_and_validate(parsed, resolve_host)
    
    current_url = url
    hops = 0
    max_hops = 5
    
    while hops < max_hops:
        hops += 1
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")
            
            current_url = _resolve_location(location, current_url)
            parsed, hostname, port = _validate_url(current_url)
            _resolve_and_validate(parsed, resolve_host)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
    
    raise ValueError("Too many redirects")
