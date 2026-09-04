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
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Invalid port")
    
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials not allowed")
    
    if not parsed.hostname:
        raise ValueError("Missing hostname")
    
    return parsed, default_port

def _validate_host(hostname, resolve_host):
    try:
        ips = resolve_host(hostname)
    except Exception:
        raise ValueError("DNS resolution failed")
    
    if not ips:
        raise ValueError("No DNS results")
    
    for ip_str in ips:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError("Invalid IP address")
        
        if ip.is_private:
            raise ValueError("Private IP address")
        if ip.is_loopback:
            raise ValueError("Loopback IP address")
        if ip.is_link_local:
            raise ValueError("Link local IP address")
        if ip.is_multicast:
            raise ValueError("Multicast IP address")
        if ip.is_reserved:
            raise ValueError("Reserved IP address")
        if ip.is_unspecified:
            raise ValueError("Unspecified IP address")
        if ip.version == 4:
            if ip == ipaddress.ip_address('0.0.0.0'):
                raise ValueError("Unspecified IP address")
        if ip.version == 6:
            if ip.ipv4_mapped is not None:
                mapped = ip.ipv4_mapped
                if mapped.is_private or mapped.is_loopback or mapped.is_link_local or mapped.is_multicast or mapped.is_reserved or mapped.is_unspecified:
                    raise ValueError("IPv4 mapped private address")
    
    return ips

def _resolve_location(location, current_url):
    return urllib.parse.urljoin(current_url, location)

def fetch_text(url, transport, resolve_host):
    parsed, default_port = _validate_url(url)
    _validate_host(parsed.hostname, resolve_host)
    
    current_url = url
    hops = 0
    max_hops = 5
    
    while hops < max_hops:
        hops += 1
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            location = None
            for name, value in headers:
                if name.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Missing Location header")
            
            current_url = _resolve_location(location, current_url)
            parsed, default_port = _validate_url(current_url)
            _validate_host(parsed.hostname, resolve_host)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
    
    raise ValueError("Too many redirects")
