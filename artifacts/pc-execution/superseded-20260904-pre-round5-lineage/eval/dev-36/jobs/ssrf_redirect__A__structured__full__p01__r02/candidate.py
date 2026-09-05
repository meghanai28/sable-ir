import socket
import urllib.parse
from urllib.parse import urlparse

def fetch_text(url: str, transport, resolve_host) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme
    host = parsed.hostname
    port = parsed.port
    default_port = {'http': 80, 'https': 443}.get(scheme)

    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS are allowed")

    if port is None:
        port = default_port

    if port != default_port:
        raise ValueError("Only default ports are allowed")

    if not host:
        raise ValueError("Invalid URL")

    resolved_ips = resolve_host(host)
    if not resolved_ips:
        raise ValueError("Failed to resolve hostname")

    initial_host = host
    initial_port = port
    initial_scheme = scheme

    try:
        if scheme == 'http':
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((resolved_ips[0], port))
            request_line = f"GET {url} HTTP/1.1\r\nHost: {host}\r\n\r\n"
            sock.send(request_line.encode('utf-8'))
            response = sock.recv(4096).decode('utf-8')
            status_line = response.split('\r\n')[0]
            status_code = int(status_line.split(' ')[1])
        else:
            sock = socket.create_connection((resolved_ips[0], port), timeout=5.0)
            request_line = f"GET {url} HTTP/1.1\r\nHost: {host}\r\n\r\n"
            sock.send(request_line.encode('utf-8'))
            response = sock.recv(4096).decode('utf-8')
            status_line = response.split('\r\n')[0]
            status_code = int(status_line.split(' ')[1])

        if status_code != 200:
            raise ValueError("Status code is not 200")

        body = response.split('\r\n\r\n')[1] if '\r\n\r\n' in response else response.split('\r\n')[1]

        return body
    except Exception as e:
        raise ValueError(f"Request failed: {e}")
