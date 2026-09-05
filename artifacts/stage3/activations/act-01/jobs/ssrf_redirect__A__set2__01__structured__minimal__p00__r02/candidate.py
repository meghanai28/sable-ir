import socket
import urllib.parse
from typing import Tuple

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname
    port = parsed.port

    if not hostname:
        raise ValueError("Invalid URL: missing hostname")

    if scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")

    if scheme == "http":
        if port != 80:
            raise ValueError("HTTP requests must use port 80")
        target_port = 80
    elif scheme == "https":
        if port != 443:
            raise ValueError("HTTPS requests must use port 443")
        target_port = 443
    else:
        raise ValueError("Unsupported scheme")

    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Failed to resolve hostname")

    if isinstance(ip_addresses, str):
        ip_addresses = [ip_addresses]

    for ip in ip_addresses:
        try:
            if scheme == "http":
                addr = ("http://" + hostname + ":" + str(target_port),)
            else:
                addr = ("https://" + hostname + ":" + str(target_port),)
            response = transport(url)
            status, headers, body = response
            if status == 200:
                return body
            raise ValueError("Unexpected status code")
        except (socket.error, ConnectionRefusedError, OSError):
            continue

    raise ValueError("Connection failed")
