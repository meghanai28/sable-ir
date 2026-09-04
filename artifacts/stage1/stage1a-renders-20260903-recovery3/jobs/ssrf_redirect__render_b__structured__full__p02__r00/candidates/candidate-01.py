import ipaddress
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


def _validate_and_reconstruct(parsed_url):
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
    
    path = parsed_url.path
    if path == '':
        path = '/'
    
    query = parsed_url.query
    fragment = parsed_url.fragment
    
    netloc = hostname
    if port is not None:
        netloc = f"{hostname}:{port}"
    
    reconstructed = urllib.parse.urlunsplit((
        scheme,
        netloc,
        path,
        query,
        fragment
    ))
    
    return reconstructed, hostname


def _resolve_and_validate_host(hostname, resolve_host):
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Host resolution failed")
    
    if not ip_addresses:
        raise ValueError("Host resolution returned no addresses")
    
    for ip_str in ip_addresses:
        if not _is_public_address(ip_str):
            raise ValueError("Non-public IP address")
    
    return True


def fetch_text(url, transport, resolve_host):
    current_url = url
    hop_count = 0
    max_hops = 5
    
    while True:
        try:
            parsed = urllib.parse.urlparse(current_url)
        except Exception:
            raise ValueError("URL parsing failed")
        
        validated_url, hostname = _validate_and_reconstruct(parsed)
        
        _resolve_and_validate_host(hostname, resolve_host)
        
        try:
            status, headers, body = transport(validated_url)
        except Exception:
            raise ValueError("Transport failed")
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            hop_count += 1
            if hop_count > max_hops:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect without Location header")
            
            try:
                current_url = urllib.parse.urljoin(validated_url, location)
            except Exception:
                raise ValueError("Location resolution failed")
            
            continue
        
        raise ValueError(f"Unexpected status: {status}")
