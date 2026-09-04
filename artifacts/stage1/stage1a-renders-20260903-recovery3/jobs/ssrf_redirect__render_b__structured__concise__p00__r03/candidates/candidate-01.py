import urllib.parse
import ipaddress

DEFAULT_PORTS = {
    'http': 80,
    'https': 443,
}

MAX_REDIRECTS = 5

def _validate_scheme_port(url):
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in DEFAULT_PORTS:
        raise ValueError("Invalid scheme")
    port = parsed.port
    if port is None:
        port = DEFAULT_PORTS[scheme]
    if port != DEFAULT_PORTS[scheme]:
        raise ValueError("Non-default port")
    return parsed, scheme, port

def _validate_host(hostname, resolve_host):
    if not hostname:
        raise ValueError("Empty hostname")
    try:
        addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("DNS resolution failed")
    if not addresses:
        raise ValueError("No addresses resolved")
    for addr in addresses:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            raise ValueError("Invalid IP address from DNS")
        if ip.is_private:
            raise ValueError("Private address")
        if ip.is_loopback:
            raise ValueError("Loopback address")
        if ip.is_reserved:
            raise ValueError("Reserved address")
        if ip.is_multicast:
            raise ValueError("Multicast address")
        if ip.is_link_local:
            raise ValueError("Link-local address")
        if ip.version == 4:
            if ip == ipaddress.ip_address('0.0.0.0'):
                raise ValueError("Unspecified address")
        if ip.version == 6:
            if ip == ipaddress.ip_address('::'):
                raise ValueError("Unspecified address")
            if ip.ipv4_mapped is not None:
                mapped = ip.ipv4_mapped
                if mapped.is_private or mapped.is_loopback or mapped.is_reserved or mapped.is_multicast or mapped.is_link_local or mapped == ipaddress.ip_address('0.0.0.0'):
                    raise ValueError("IPv4-mapped invalid address")
    return addresses

def _resolve_location(location, base_url):
    joined = urllib.parse.urljoin(base_url, location)
    parsed = urllib.parse.urlparse(joined)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Invalid redirect location")
    return joined

def _check_credential_restriction(base_parsed, new_parsed):
    base_userinfo = base_parsed.username or base_parsed.password
    new_userinfo = new_parsed.username or new_parsed.password
    if base_userinfo and not new_userinfo:
        pass
    elif new_userinfo and not base_userinfo:
        raise ValueError("Credentials added in redirect")
    return

def fetch_text(url, transport, resolve_host):
    current_url = url
    hops = 0
    
    while hops <= MAX_REDIRECTS:
        parsed, scheme, port = _validate_scheme_port(current_url)
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("No hostname")
        
        _validate_host(hostname, resolve_host)
        
        status, headers, body = transport(current_url)
        
        if 300 <= status < 400:
            if hops >= MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            location = None
            for key, value in headers:
                if key.lower() == 'location':
                    location = value
                    break
            if location is None:
                raise ValueError("Redirect without Location header")
            next_url = _resolve_location(location, current_url)
            next_parsed, next_scheme, next_port = _validate_scheme_port(next_url)
            next_hostname = next_parsed.hostname
            if next_hostname is None:
                raise ValueError("Redirect location has no hostname")
            _validate_host(next_hostname, resolve_host)
            _check_credential_restriction(parsed, next_parsed)
            current_url = next_url
            hops += 1
            continue
        
        if status == 200:
            return body
        
        raise ValueError(f"Unexpected status: {status}")
    
    raise ValueError("Too many redirects")
