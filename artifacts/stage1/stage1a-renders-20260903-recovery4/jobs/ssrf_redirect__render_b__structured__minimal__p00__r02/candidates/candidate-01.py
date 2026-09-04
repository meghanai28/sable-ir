import ipaddress
import urllib.parse

def _validate_url(url, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Scheme must be http or https")
    
    default_port = 80 if parsed.scheme == 'http' else 443
    port = parsed.port
    if port is None:
        port = default_port
    if port != default_port:
        raise ValueError("Non-default port not allowed")
    
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials not allowed in URL")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    try:
        ips = resolve_host(hostname)
    except Exception:
        raise ValueError("DNS resolution failed")
    
    if not ips:
        raise ValueError("No IP addresses returned")
    
    for ip_str in ips:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError("Invalid IP address returned")
        
        if ip.is_private:
            raise ValueError("Private IP address not allowed")
        if ip.is_loopback:
            raise ValueError("Loopback IP address not allowed")
        if ip.is_link_local:
            raise ValueError("Link-local IP address not allowed")
        if ip.is_multicast:
            raise ValueError("Multicast IP address not allowed")
        if ip.is_reserved:
            raise ValueError("Reserved IP address not allowed")
        if ip.is_unspecified:
            raise ValueError("Unspecified IP address not allowed")
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
            ipv4 = ip.ipv4_mapped
            if ipv4.is_private or ipv4.is_loopback or ipv4.is_link_local or ipv4.is_multicast or ipv4.is_reserved or ipv4.is_unspecified:
                raise ValueError("IPv4-mapped private IP address not allowed")
        if isinstance(ip, ipaddress.IPv6Address) and ip.sixtofour is not None:
            ipv4 = ip.sixtofour
            if ipv4.is_private or ipv4.is_loopback or ipv4.is_link_local or ipv4.is_multicast or ipv4.is_reserved or ipv4.is_unspecified:
                raise ValueError("6to4-derived private IP address not allowed")
        if isinstance(ip, ipaddress.IPv6Address) and ip.teredo is not None:
            ipv4 = ip.teredo[1]
            if ipv4.is_private or ipv4.is_loopback or ipv4.is_link_local or ipv4.is_multicast or ipv4.is_reserved or ipv4.is_unspecified:
                raise ValueError("Teredo-derived private IP address not allowed")
    
    return parsed

def fetch_text(url, transport, resolve_host):
    _validate_url(url, resolve_host)
    current_url = url
    
    for hop in range(5):
        parsed = urllib.parse.urlparse(current_url)
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect without Location header")
            
            new_url = urllib.parse.urljoin(current_url, location)
            _validate_url(new_url, resolve_host)
            current_url = new_url
            continue
        
        raise ValueError(f"Unexpected status: {status}")
    
    raise ValueError("Too many redirects")
