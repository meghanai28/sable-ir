import ipaddress
import urllib.parse

def _is_public_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    
    if ip.is_private:
        return False
    if ip.is_loopback:
        return False
    if ip.is_link_local:
        return False
    if ip.is_multicast:
        return False
    if ip.is_unspecified:
        return False
    
    return True

def _validate_and_canonicalize(url):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    default_port = 80 if scheme == 'http' else 443
    
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Userinfo not allowed")
    
    if parsed.hostname is None:
        raise ValueError("Missing hostname")
    
    hostname = parsed.hostname.lower()
    
    port = parsed.port
    if port is None:
        port = default_port
    if port != default_port:
        raise ValueError("Non-default port not allowed")
    
    netloc = hostname
    
    path = parsed.path
    if not path:
        path = '/'
    
    query = parsed.query
    fragment = parsed.fragment
    
    canonical = urllib.parse.urlunparse((
        scheme,
        netloc,
        path,
        '',
        query,
        fragment
    ))
    
    return canonical, hostname

def _resolve_location(location, base_url):
    return urllib.parse.urljoin(base_url, location)

def fetch_text(url, transport, resolve_host):
    current_url = url
    hop_count = 0
    
    while True:
        canonical_url, hostname = _validate_and_canonicalize(current_url)
        
        try:
            ip_addresses = resolve_host(hostname)
        except Exception:
            raise ValueError("Host resolution failed")
        
        if not ip_addresses:
            raise ValueError("No IP addresses returned")
        
        for ip_str in ip_addresses:
            if not _is_public_ip(ip_str):
                raise ValueError("Non-public IP address")
        
        status, headers, body = transport(canonical_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            hop_count += 1
            if hop_count > 5:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect without Location header")
            
            current_url = _resolve_location(location, canonical_url)
            continue
        
        raise ValueError("Non-200 non-redirect status")
