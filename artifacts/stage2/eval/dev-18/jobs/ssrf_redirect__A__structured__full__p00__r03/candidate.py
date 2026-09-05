import urllib.parse
import urllib.request
import urllib.error
import socket
import ssl
import struct

def resolve_host(hostname):
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        ips = []
        for family, _, _, _, sockaddr in addr_info:
            ip = sockaddr[0]
            if ':' not in ip:
                ips.append(ip)
            else:
                ips.append(ip)
        return ips
    except socket.gaierror:
        raise ValueError("Host resolution failed")

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    path = parsed.path

    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    if '://' in host:
        raise ValueError("Invalid host format")

    if not host:
        raise ValueError("Empty host")

    ips = resolve_host(host)
    if len(ips) != 1:
        raise ValueError("Multiple IP addresses or resolution failed")
    resolved_ip = ips[0]

    if parsed.port is None:
        port = 80 if scheme == 'http' else 443
    else:
        port = parsed.port

    if port not in (80, 443):
        raise ValueError("Non-default port")

    if parsed.netloc:
        path = parsed.path
    else:
        path = parsed.path

    if '..' in path:
        raise ValueError("Invalid path segments")

    if not path:
        path = '/'

    full_url = f"{scheme}://{host}:{port}{path}"

    req = urllib.request.Request(full_url)
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            if status != 200:
                raise ValueError(f"Status {status} is not 200")
            body = response.read().decode('utf-8')
            return body
    except urllib.error.HTTPError as e:
        if e.code != 301 and e.code != 302:
            raise ValueError(f"Unexpected status {e.code}")
        raise ValueError("Redirect not allowed")
    except urllib.error.URLError as e:
        raise ValueError(f"Connection failed: {e.reason}")
