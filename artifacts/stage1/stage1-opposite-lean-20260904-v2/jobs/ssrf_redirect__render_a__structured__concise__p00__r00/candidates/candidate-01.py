import urllib.parse

_DEFAULT_PORTS = {'http': 80, 'https': 443}
_MAX_REDIRECTS = 5

def _is_public_address(ip: str) -> bool:
    if ':' in ip:
        return _is_public_ipv6(ip)
    return _is_public_ipv4(ip)

def _is_public_ipv4(ip: str) -> bool:
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        octets = [int(p) for p in parts]
    except ValueError:
        return False
    for o in octets:
        if not 0 <= o <= 255:
            return False
    a, b, c, d = octets
    if a == 0:
        return False
    if a == 10:
        return False
    if a == 172 and 16 <= b <= 31:
        return False
    if a == 192 and b == 168:
        return False
    if a == 127:
        return False
    if a == 169 and b == 254:
        return False
    if a == 192 and b == 0 and c == 2:
        return False
    if a == 198 and b == 51 and c == 100:
        return False
    if a == 203 and b == 0 and c == 113:
        return False
    if a == 100 and 64 <= b <= 127:
        return False
    if a == 192 and b == 88 and c == 99:
        return False
    if a == 198 and b == 18 and 0 <= c <= 31:
        return False
    if a >= 224:
        return False
    if a == 255 and b == 255 and c == 255 and d == 255:
        return False
    return True

def _is_public_ipv6(ip: str) -> bool:
    if ip == '::1':
        return False
    if ip.startswith('fe80:'):
        return False
    if ip.startswith('fc') or ip.startswith('fd'):
        return False
    if ip.startswith('ff'):
        return False
    if ip == '::':
        return False
    if ip.lower().startswith('2001:db8:'):
        return False
    if ip.lower().startswith('2001:0:'):
        return False
    if ip.lower().startswith('100:'):
        return False
    if ip.lower().startswith('64:ff9b:1:'):
        return False
    return True

def _validate_url(url: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError('Invalid scheme')
    if not parsed.hostname:
        raise ValueError('Missing hostname')
    port = parsed.port
    if port is None:
        port = _DEFAULT_PORTS[parsed.scheme]
    if port != _DEFAULT_PORTS[parsed.scheme]:
        raise ValueError('Non-default port')
    if parsed.username is not None or parsed.password is not None:
        raise ValueError('Credentials not allowed')
    return parsed

def _resolve_and_validate_host(hostname: str, resolve_host) -> None:
    try:
        addresses = resolve_host(hostname)
    except Exception:
        raise ValueError('Host resolution failed')
    if not addresses:
        raise ValueError('No addresses resolved')
    for addr in addresses:
        if not _is_public_address(addr):
            raise ValueError('Non-public address resolved')

def _resolve_location(location: str, current_url: str) -> str:
    resolved = urllib.parse.urljoin(current_url, location)
    return resolved

def fetch_text(url, transport, resolve_host) -> str:
    current_url = url
    hops = 0
    
    while hops < _MAX_REDIRECTS:
        parsed = _validate_url(current_url)
        _resolve_and_validate_host(parsed.hostname, resolve_host)
        
        status, headers, body = transport(current_url)
        
        if 300 <= status < 400:
            hops += 1
            if hops >= _MAX_REDIRECTS:
                raise ValueError('Too many redirects')
            location = headers.get('Location')
            if not location:
                raise ValueError('Redirect without Location header')
            current_url = _resolve_location(location, current_url)
            continue
        
        if status != 200:
            raise ValueError(f'Non-200 status: {status}')
        
        return body
    
    raise ValueError('Too many redirects')
