import ipaddress
import re
import urllib.parse


def _is_public_address(ip_str):
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    
    if addr.is_private:
        return False
    if addr.is_loopback:
        return False
    if addr.is_link_local:
        return False
    if addr.is_multicast:
        return False
    if addr.is_unspecified:
        return False
    
    return True


def _validate_and_canonicalize(parsed_url):
    scheme = parsed_url.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    default_port = 80 if scheme == 'http' else 443
    
    if parsed_url.username is not None or parsed_url.password is not None:
        raise ValueError("Userinfo not allowed")
    
    hostname = parsed_url.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    port = parsed_url.port
    if port is not None and port != default_port:
        raise ValueError("Non-default port not allowed")
    
    netloc = hostname.lower()
    if port is not None:
        netloc = netloc + ':' + str(port)
    
    canonical = urllib.parse.urlunparse((
        scheme,
        netloc,
        parsed_url.path,
        parsed_url.params,
        parsed_url.query,
        parsed_url.fragment,
    ))
    
    return canonical, hostname


def _resolve_and_validate_host(hostname, resolve_host):
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Host resolution failed")
    
    if not ip_addresses:
        raise ValueError("No IP addresses returned")
    
    for ip_str in ip_addresses:
        if not _is_public_address(ip_str):
            raise ValueError("Non-public IP address")
    
    return ip_addresses


def fetch_text(url, transport, resolve_host):
    max_redirects = 5
    hop_count = 0
    current_url = url
    
    while True:
        try:
            parsed = urllib.parse.urlparse(current_url)
        except Exception:
            raise ValueError("URL parsing failed")
        
        if not parsed.scheme:
            raise ValueError("Missing scheme")
        
        canonical_url, hostname = _validate_and_canonicalize(parsed)
        
        _resolve_and_validate_host(hostname, resolve_host)
        
        status, headers, body = transport(canonical_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            hop_count += 1
            if hop_count > max_redirects:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect without Location header")
            
            try:
                current_url = urllib.parse.urljoin(canonical_url, location)
            except Exception:
                raise ValueError("Location resolution failed")
            
            continue
        
        raise ValueError("Non-200 non-redirect status")
