import urllib.parse

_DEFAULT_PORTS = {
    'http': 80,
    'https': 443,
}

_MAX_REDIRECTS = 5

def _is_public_ip(ip_str):
    try:
        parts = ip_str.split('.')
        if len(parts) != 4:
            return False
        octets = [int(p) for p in parts]
        if not all(0 <= o <= 255 for o in octets):
            return False
    except (ValueError, AttributeError):
        return False

    if octets[0] == 0:
        return False
    if octets[0] == 10:
        return False
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return False
    if octets[0] == 192 and octets[1] == 168:
        return False
    if octets[0] == 127:
        return False
    if octets[0] == 169 and octets[1] == 254:
        return False
    if octets[0] >= 224:
        return False

    return True

def _validate_url(url, base_url=None):
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme:
        if base_url is None:
            raise ValueError("Missing scheme")
        parsed = urllib.parse.urlparse(urllib.parse.urljoin(base_url, url))
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    port = parsed.port
    if port is None:
        port = _DEFAULT_PORTS[parsed.scheme]
    if port != _DEFAULT_PORTS[parsed.scheme]:
        raise ValueError("Non-default port")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    netloc = hostname
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials not allowed")
    
    return parsed, hostname, port

def _resolve_and_validate(hostname, resolve_host):
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError("No DNS resolution")
    for ip in ips:
        if not _is_public_ip(ip):
            raise ValueError("Non-public address")
    return ips

def _build_url(parsed):
    netloc = parsed.hostname
    return urllib.parse.urlunparse((
        parsed.scheme,
        netloc,
        parsed.path or '/',
        parsed.params,
        parsed.query,
        parsed.fragment,
    ))

def fetch_text(url, transport, resolve_host):
    current_url = url
    redirects = 0
    
    parsed, hostname, port = _validate_url(current_url)
    _resolve_and_validate(hostname, resolve_host)
    
    while True:
        target_url = _build_url(parsed)
        status, headers, body = transport(target_url)
        
        if 300 <= status < 400:
            redirects += 1
            if redirects > _MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")
            
            new_parsed, new_hostname, new_port = _validate_url(location, current_url)
            _resolve_and_validate(new_hostname, resolve_host)
            
            current_url = _build_url(new_parsed)
            parsed = new_parsed
            continue
        
        if status != 200:
            raise ValueError(f"Non-200 status: {status}")
        
        return body
