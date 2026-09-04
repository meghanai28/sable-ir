import subprocess
import urllib.parse
import ipaddress

def run_text_utility(executable: str, arguments: list[str]) -> str:
    ALLOWED_UTILITIES = {
        'curl',
        'wget',
    }
    
    if executable not in ALLOWED_UTILITIES:
        raise ValueError(f"Disallowed executable: {executable}")
    
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        check=True
    )
    
    return result.stdout


def resolve_host(hostname: str) -> list[str]:
    import socket
    return socket.gethostbyname_ex(hostname)[2]


def transport(url: str) -> tuple[int, dict[str, str], str]:
    import urllib.request
    req = urllib.request.Request(url, method='GET')
    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            headers = dict(response.headers)
            body = response.read().decode('utf-8', errors='replace')
            return status, headers, body
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode('utf-8', errors='replace')


def fetch_url(untrusted_url: str) -> str:
    MAX_REDIRECTS = 5
    DEFAULT_PORTS = {
        'http': 80,
        'https': 443,
    }
    
    current_url = untrusted_url
    hops = 0
    
    while hops < MAX_REDIRECTS:
        parsed = urllib.parse.urlparse(current_url)
        
        # Validate scheme
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError(f"Disallowed scheme: {scheme}")
        
        # Validate port
        port = parsed.port
        if port is None:
            port = DEFAULT_PORTS[scheme]
        if port != DEFAULT_PORTS[scheme]:
            raise ValueError(f"Disallowed non-default port: {port}")
        
        # Validate no credentials
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials in URL are not allowed")
        
        # Validate hostname exists
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        # Resolve and validate host addresses
        try:
            addresses = resolve_host(hostname)
        except Exception:
            raise ValueError(f"Failed to resolve hostname: {hostname}")
        
        for addr in addresses:
            ip = ipaddress.ip_address(addr)
            if ip.is_private:
                raise ValueError(f"Private address not allowed: {addr}")
            if ip.is_loopback:
                raise ValueError(f"Loopback address not allowed: {addr}")
            if ip.is_reserved:
                raise ValueError(f"Reserved address not allowed: {addr}")
            if ip.is_multicast:
                raise ValueError(f"Multicast address not allowed: {addr}")
            if ip.is_link_local:
                raise ValueError(f"Link-local address not allowed: {addr}")
            if ip.version == 6 and ip.ipv4_mapped is not None:
                mapped = ipaddress.ip_address(str(ip.ipv4_mapped))
                if mapped.is_private or mapped.is_loopback or mapped.is_reserved or mapped.is_multicast or mapped.is_link_local:
                    raise ValueError(f"IPv4-mapped private address not allowed: {addr}")
        
        # Build canonical URL for transport
        netloc = hostname
        if parsed.path:
            path = parsed.path
        else:
            path = '/'
        query = parsed.query
        
        canonical_url = urllib.parse.urlunparse((
            scheme,
            netloc,
            path,
            '',
            query,
            ''
        ))
        
        # Make transport request
        status, headers, body = transport(canonical_url)
        
        # Handle redirect
        if status in (301, 302, 303, 307, 308):
            hops += 1
            if hops >= MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location') or headers.get('location')
            if location is None:
                raise ValueError("Redirect without Location header")
            
            # Resolve Location against current URL
            current_url = urllib.parse.urljoin(current_url, location)
            continue
        
        # Check final status
        if status != 200:
            raise ValueError(f"Non-200 status: {status}")
        
        return body
    
    raise ValueError("Too many redirects")
